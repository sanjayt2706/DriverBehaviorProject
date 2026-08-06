"""
Backend/app/crud/sensor.py
All `raw_sensor_data` queries. Bulk insert per Database.md "Operational notes" -
row-by-row ORM inserts for 500-row batches at ~90k rows/trip is the most
likely performance failure in this build.

KNOWN GAP: resent batches (same batch_index sent twice after a dropped
connection) are not deduplicated yet. Fine for a single-demo MVP where the
app controls retry behaviour; revisit before any multi-device use.
"""
from typing import List
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.raw_sensor_data import RawSensorData
from app.schemas.sensor import SensorSample


def bulk_insert_samples(db: Session, trip_id: str, samples: List[SensorSample]) -> int:
    rows = [
        {
            "trip_id": trip_id,
            "timestamp": s.timestamp,
            "latitude": s.latitude,
            "longitude": s.longitude,
            "speed": s.speed,
            "accel_x": s.accel_x,
            "accel_y": s.accel_y,
            "accel_z": s.accel_z,
            "gyro_x": s.gyro_x,
            "gyro_y": s.gyro_y,
            "gyro_z": s.gyro_z,
        }
        for s in samples
    ]
    db.bulk_insert_mappings(RawSensorData, rows)
    db.commit()
    return len(rows)


def count_samples(db: Session, trip_id: str) -> int:
    return db.query(func.count(RawSensorData.id)).filter(RawSensorData.trip_id == trip_id).scalar() or 0


def get_samples_ordered(db: Session, trip_id: str) -> List[RawSensorData]:
    return (
        db.query(RawSensorData)
        .filter(RawSensorData.trip_id == trip_id)
        .order_by(RawSensorData.timestamp.asc())
        .all()
    )
