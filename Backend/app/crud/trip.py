"""
Backend/app/crud/trip.py
All `trips` table queries live here - routes never touch SQL directly
(Architecture.md Section 4, Layer 3 responsibilities).
"""
from typing import Optional
from sqlalchemy.orm import Session

from app.models.trip import Trip, TripStatus
from app.utils.time import utc_now_iso


def create_trip(
    db: Session, trip_id: str, user_id: str, device_model: Optional[str], start_time: str
) -> Trip:
    trip = Trip(
        trip_id=trip_id,
        user_id=user_id,
        device_model=device_model,
        start_time=start_time,
        status=TripStatus.CREATED,
        created_at=utc_now_iso(),
    )
    db.add(trip)
    db.commit()
    db.refresh(trip)
    return trip


def get_trip(db: Session, trip_id: str) -> Optional[Trip]:
    return db.query(Trip).filter(Trip.trip_id == trip_id).first()


def set_status(db: Session, trip: Trip, status: str) -> Trip:
    trip.status = status
    db.commit()
    db.refresh(trip)
    return trip


def set_end_time_and_count(
    db: Session, trip: Trip, end_time: Optional[str], sample_count: int
) -> Trip:
    if end_time:
        trip.end_time = end_time
    trip.sample_count = sample_count
    db.commit()
    db.refresh(trip)
    return trip
