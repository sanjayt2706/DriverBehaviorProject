"""
Backend/app/processing/preprocessing.py
Layer 4, step 1: clean - forward-fill GPS. See Architecture.md Section 4.
"""
from typing import List, Dict
from app.models.raw_sensor_data import RawSensorData


def clean_and_forward_fill(samples: List[RawSensorData]) -> List[Dict]:
    """
    - Drops rows with an impossible speed (< 0 or > 200 km/h).
    - Forward-fills latitude/longitude/speed across IMU-only rows, since
      GPS runs at 1 Hz against a 50 Hz IMU.
    Input must already be ordered by timestamp. Returns plain dicts.
    """
    cleaned: List[Dict] = []
    last_lat = last_lon = last_speed = None

    for s in samples:
        if s.speed is not None and (s.speed < 0 or s.speed > 200):
            continue  # drop impossible reading

        lat = s.latitude if s.latitude is not None else last_lat
        lon = s.longitude if s.longitude is not None else last_lon
        speed = s.speed if s.speed is not None else last_speed

        if s.latitude is not None:
            last_lat = s.latitude
        if s.longitude is not None:
            last_lon = s.longitude
        if s.speed is not None:
            last_speed = s.speed

        cleaned.append({
            "timestamp": s.timestamp,
            "latitude": lat,
            "longitude": lon,
            "speed": speed,
            "accel_x": s.accel_x, "accel_y": s.accel_y, "accel_z": s.accel_z,
            "gyro_x": s.gyro_x, "gyro_y": s.gyro_y, "gyro_z": s.gyro_z,
        })

    return cleaned
