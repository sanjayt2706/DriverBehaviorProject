"""
Backend/app/models/trip.py
SQLAlchemy model for the `trips` table. See docs/Database.md Section 1.
"""
from sqlalchemy import Column, String, Float, Integer
from sqlalchemy.orm import relationship

from app.database import Base


class TripStatus:
    """Locked status enum, docs/Database.md Section 1."""
    CREATED = "CREATED"
    UPLOADING = "UPLOADING"
    UPLOADED = "UPLOADED"
    PROCESSING = "PROCESSING"
    PROCESSED = "PROCESSED"
    FAILED = "FAILED"


class Trip(Base):
    __tablename__ = "trips"

    trip_id = Column(String, primary_key=True)  # client-generated (Android app)
    user_id = Column(String, nullable=False, index=True)
    device_model = Column(String, nullable=True)
    start_time = Column(String, nullable=False)  # ISO 8601 UTC
    end_time = Column(String, nullable=True)
    duration_s = Column(Float, nullable=True)
    distance_km = Column(Float, nullable=True)
    sample_count = Column(Integer, default=0)
    # Comma-separated batch_index values already inserted, so a resent batch
    # (dropped connection after the server committed but before the client
    # saw the response) is ignored instead of double-inserted - API.md
    # "Duplicate batch_index values are ignored rather than double-inserted."
    received_batches = Column(String, nullable=False, default="")
    status = Column(String, nullable=False, default=TripStatus.CREATED)
    created_at = Column(String, nullable=False)
    processed_at = Column(String, nullable=True)

    raw_samples = relationship(
        "RawSensorData", back_populates="trip", cascade="all, delete-orphan"
    )
    features = relationship(
        "Feature", back_populates="trip", cascade="all, delete-orphan"
    )
    prediction = relationship(
        "Prediction", back_populates="trip", uselist=False, cascade="all, delete-orphan"
    )
    shap_explanations = relationship(
        "ShapExplanation", back_populates="trip", cascade="all, delete-orphan"
    )
