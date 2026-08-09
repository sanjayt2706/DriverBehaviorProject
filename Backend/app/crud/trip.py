"""
Backend/app/crud/trip.py
All `trips` table queries live here - routes never touch SQL directly
(Architecture.md Section 4, Layer 3 responsibilities).
"""
from typing import Optional
from sqlalchemy import text
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


def try_claim_batch(db: Session, trip: Trip, batch_index: int) -> bool:
    """
    Atomically claims batch_index for this trip if it hasn't been claimed yet.
    Checking (`has_batch`) and recording (`mark_batch_received`) used to be two
    separate reads/writes, which let two concurrent requests for the same
    batch_index - exactly the dropped-connection-retry case this exists to
    handle - both see "not yet received" before either committed, and both
    insert. Doing it as a single UPDATE ... WHERE NOT already-present makes
    SQLite's own write-lock serialize concurrent attempts: only one request's
    UPDATE can affect a row, so only one gets True.

    Returns True if this call just claimed it (caller must insert the batch),
    False if it was already claimed by an earlier request (caller must skip -
    it's already been inserted).
    """
    batch_str = str(batch_index)
    result = db.execute(
        text(
            """
            UPDATE trips
            SET received_batches = CASE
                    WHEN received_batches = '' THEN :batch_str
                    ELSE received_batches || ',' || :batch_str
                END
            WHERE trip_id = :trip_id
              AND (',' || received_batches || ',') NOT LIKE :like_pattern
            """
        ),
        {
            "trip_id": trip.trip_id,
            "batch_str": batch_str,
            "like_pattern": f"%,{batch_str},%",
        },
    )
    db.commit()
    db.refresh(trip)
    return result.rowcount == 1
