"""
ML/src/step02_clean.py
Pipeline A, step 2: convert one UAH-DriveSet trip into the locked sensor
schema (accel_x/y/z, gyro_x/y/z; m/s^2, rad/s) used everywhere else in
this project. See Documentation/Dataset Specification.md, section
"Preprocessing required before training", for why each transform below
is necessary - this is the ONLY dataset-specific adapter in the pipeline.
Everything downstream (step04 onward) calls the exact same
Backend/app/processing code that runs at inference time.

Axis remap (UAH car-referenced axes -> project convention):
    UAH Z (longitudinal, accel/brake) -> accel_x
    UAH Y (lateral, turning)          -> accel_y
    UAH X (vertical)                  -> accel_z
Unit: UAH logs acceleration in G -> multiplied by 9.80665 for m/s^2.

UAH logs orientation (roll/pitch/yaw, degrees) instead of raw angular
velocity. Angular velocity is recovered by differentiating orientation
over time then converting deg/s -> rad/s. This is a documented proxy for
gyroscope output, not a real angular-rate sensor reading.

UAH's accelerometer is logged at 10 Hz (reduced from the phone's 100 Hz),
not the project's locked 50 Hz. Samples are upsampled by linear
interpolation so window sizing in windowing.py (driven by wall-clock ms,
not raw sample count) sees a comparable sample density to production data.

Timestamps are route-relative seconds (as UAH logs them), converted here
to route-relative milliseconds - not real calendar time. This is fine for
windowing (which only uses time differences) but means trip.duration_s
computed later reflects the recording only, not a wall-clock date.
"""
import math
from pathlib import Path
from types import SimpleNamespace
from typing import List

G_TO_MS2 = 9.80665
TARGET_HZ = 50  # matches Backend/app/config.py IMU_HZ


def _load_gps(gps_file: Path) -> List[dict]:
    """RAW_GPS.txt columns: timestamp(s), speed(km/h), lat(deg), lon(deg), ..."""
    rows = []
    for line in gps_file.read_text().splitlines():
        parts = line.strip().split()
        if len(parts) < 4:
            continue
        ts_s, speed, lat, lon = (float(parts[0]), float(parts[1]),
                                  float(parts[2]), float(parts[3]))
        rows.append({"t": ts_s, "lat": lat, "lon": lon, "speed": speed})
    return rows


def _load_accel(accel_file: Path) -> List[dict]:
    """
    RAW_ACCELEROMETERS.txt columns: timestamp(s), active-bool, ax(G), ay(G),
    az(G), ax_kf(G), ay_kf(G), az_kf(G), roll(deg), pitch(deg), yaw(deg).
    Unfiltered ax/ay/az (columns 3-5) are used, not the Kalman-filtered ones,
    to keep the noise characteristics closer to a raw phone sensor stream.
    """
    rows = []
    for line in accel_file.read_text().splitlines():
        parts = line.strip().split()
        if len(parts) < 11:
            continue
        ts_s = float(parts[0])
        ax_g, ay_g, az_g = float(parts[2]), float(parts[3]), float(parts[4])
        roll, pitch, yaw = float(parts[8]), float(parts[9]), float(parts[10])
        rows.append({"t": ts_s, "ax_g": ax_g, "ay_g": ay_g, "az_g": az_g,
                      "roll": roll, "pitch": pitch, "yaw": yaw})
    return rows


def _interpolate(rows: List[dict], key: str, t_query: List[float]) -> List[float]:
    """Linear interpolation. `rows` must already be sorted by 't'."""
    ts = [r["t"] for r in rows]
    vs = [r[key] for r in rows]
    out = []
    j = 0
    n = len(ts)
    for t in t_query:
        while j < n - 2 and ts[j + 1] < t:
            j += 1
        if t <= ts[0]:
            out.append(vs[0])
        elif t >= ts[-1]:
            out.append(vs[-1])
        else:
            t0, t1 = ts[j], ts[j + 1]
            v0, v1 = vs[j], vs[j + 1]
            frac = (t - t0) / (t1 - t0) if t1 > t0 else 0.0
            out.append(v0 + frac * (v1 - v0))
    return out


def _angle_diff_deg(a: float, b: float) -> float:
    """Shortest signed difference b - a, wrapped to [-180, 180]."""
    return (b - a + 180) % 360 - 180


def clean_trip(gps_file: Path, accel_file: Path) -> List[SimpleNamespace]:
    """
    Returns a list of lightweight sample objects exposing the same
    attributes as app.models.raw_sensor_data.RawSensorData, so they can be
    passed directly into app.processing.preprocessing.clean_and_forward_fill
    unchanged - training uses the identical downstream code path as runtime.
    """
    gps_rows = _load_gps(gps_file)
    accel_rows = _load_accel(accel_file)

    if len(gps_rows) < 2 or len(accel_rows) < 2:
        return []

    t_start = accel_rows[0]["t"]
    t_end = accel_rows[-1]["t"]
    n_samples = int((t_end - t_start) * TARGET_HZ)
    if n_samples < 2:
        return []

    dt = 1.0 / TARGET_HZ
    t_query = [t_start + i * dt for i in range(n_samples)]

    ax_g = _interpolate(accel_rows, "ax_g", t_query)
    ay_g = _interpolate(accel_rows, "ay_g", t_query)
    az_g = _interpolate(accel_rows, "az_g", t_query)
    roll = _interpolate(accel_rows, "roll", t_query)
    pitch = _interpolate(accel_rows, "pitch", t_query)
    yaw = _interpolate(accel_rows, "yaw", t_query)

    lat = _interpolate(gps_rows, "lat", t_query)
    lon = _interpolate(gps_rows, "lon", t_query)
    speed = _interpolate(gps_rows, "speed", t_query)

    samples = []
    for i in range(n_samples):
        gyro_x = math.radians(_angle_diff_deg(roll[i - 1], roll[i]) / dt) if i > 0 else 0.0
        gyro_y = math.radians(_angle_diff_deg(pitch[i - 1], pitch[i]) / dt) if i > 0 else 0.0
        gyro_z = math.radians(_angle_diff_deg(yaw[i - 1], yaw[i]) / dt) if i > 0 else 0.0

        samples.append(SimpleNamespace(
            timestamp=int((t_start + i * dt) * 1000),  # route-relative ms
            latitude=lat[i],
            longitude=lon[i],
            speed=speed[i],
            accel_x=az_g[i] * G_TO_MS2,   # UAH Z (longitudinal) -> accel_x
            accel_y=ay_g[i] * G_TO_MS2,   # UAH Y (lateral)      -> accel_y
            accel_z=ax_g[i] * G_TO_MS2,   # UAH X (vertical)     -> accel_z
            gyro_x=gyro_x,
            gyro_y=gyro_y,
            gyro_z=gyro_z,
        ))

    return samples
