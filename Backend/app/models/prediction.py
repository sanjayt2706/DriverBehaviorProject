"""
Backend/app/models/prediction.py
SQLAlchemy model for the `predictions` table. See docs/Database.md Section 4.
One row per trip - what the Result screen reads.
"""
from sqlalchemy import Column, Integer, String, Float, ForeignKey
from sqlalchemy.orm import relationship

from app.database import Base


class Prediction(Base):
    __tablename__ = "predictions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    trip_id = Column(String, ForeignKey("trips.trip_id", ondelete="CASCADE"), nullable=False, unique=True)

    trip_score = Column(Float, nullable=False)
    risk_level = Column(String, nullable=False)  # LOW / MEDIUM / HIGH
    window_count = Column(Integer, nullable=False)
    pct_low = Column(Float, nullable=False)
    pct_medium = Column(Float, nullable=False)
    pct_high = Column(Float, nullable=False)
    weight_w1 = Column(Float, nullable=False)
    weight_w2 = Column(Float, nullable=False)

    harsh_braking_count = Column(Integer, default=0)
    harsh_acceleration_count = Column(Integer, default=0)
    harsh_cornering_count = Column(Integer, default=0)
    overspeeding_count = Column(Integer, default=0)

    curve_density_trip = Column(Float, nullable=True)

    model_name = Column(String, nullable=False)
    model_version = Column(String, nullable=True)
    created_at = Column(String, nullable=False)

    trip = relationship("Trip", back_populates="prediction")
