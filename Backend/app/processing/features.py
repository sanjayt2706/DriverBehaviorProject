"""
Backend/app/processing/features.py
Layer 4, step 3: statistical + behavioural features per window.
Column set is locked in Database.md Section 3. Event thresholds are
[INFERRED] placeholders in config.py - must be tuned against real drive
data once ML/ collects the dataset (Architecture.md Section 6).
"""
import math
import statistics as st
from typing import List, Dict

from app.config import (
    HARSH_BRAKE_THRESHOLD_MS2, HARSH_ACCEL_THRESHOLD_MS2,
    HARSH_CORNER_GYRO_THRESHOLD, OVERSPEED_KMH,
)


def _mag(x: float, y: float, z: float) -> float:
    return math.sqrt(x * x + y * y + z * z)


def extract_window_features(window: List[Dict]) -> Dict:
    speeds = [s["speed"] for s in window if s["speed"] is not None]
    accel_mags = [_mag(s["accel_x"], s["accel_y"], s["accel_z"]) for s in window]
    gyro_mags = [_mag(s["gyro_x"], s["gyro_y"], s["gyro_z"]) for s in window]

    # accel_x approximates longitudinal (direction of travel), accel_y lateral.
    # [INFERRED] refine once real drive data confirms typical phone mounting.
    accel_long = [s["accel_x"] for s in window]
    accel_lat = [s["accel_y"] for s in window]

    jerks = (
        [abs(accel_mags[i] - accel_mags[i - 1]) for i in range(1, len(accel_mags))]
        if len(accel_mags) > 1 else [0.0]
    )

    harsh_brake = sum(1 for a in accel_long if a <= HARSH_BRAKE_THRESHOLD_MS2)
    harsh_accel = sum(1 for a in accel_long if a >= HARSH_ACCEL_THRESHOLD_MS2)
    harsh_corner = sum(1 for s in window if abs(s["gyro_z"]) >= HARSH_CORNER_GYRO_THRESHOLD)
    overspeed = sum(1 for sp in speeds if sp >= OVERSPEED_KMH)

    return {
        "speed_mean": st.mean(speeds) if speeds else 0.0,
        "speed_max": max(speeds) if speeds else 0.0,
        "speed_std": st.pstdev(speeds) if len(speeds) > 1 else 0.0,

        "accel_mag_mean": st.mean(accel_mags),
        "accel_mag_std": st.pstdev(accel_mags) if len(accel_mags) > 1 else 0.0,
        "accel_mag_max": max(accel_mags),
        "accel_long_mean": st.mean(accel_long),
        "accel_long_min": min(accel_long),
        "accel_long_max": max(accel_long),
        "accel_lat_max": max(abs(a) for a in accel_lat),

        "jerk_mean": st.mean(jerks),
        "jerk_max": max(jerks),

        "gyro_mag_mean": st.mean(gyro_mags),
        "gyro_mag_std": st.pstdev(gyro_mags) if len(gyro_mags) > 1 else 0.0,
        "gyro_z_max": max(abs(s["gyro_z"]) for s in window),

        "harsh_brake_count": harsh_brake,
        "harsh_accel_count": harsh_accel,
        "harsh_corner_count": harsh_corner,
        "overspeed_count": overspeed,
    }
