"""
Backend/app/models/feature.py
SQLAlchemy model for the `features` table. See docs/Database.md Section 3.
One row per sliding window. predicted_label/predicted_confidence live here
rather than a sixth table, per the locked 5-table count.
"""
from sqlalchemy import Column, Integer, String, Float, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship

from app.database import Base


class Feature(Base):
    __tablename__ = "features"

    id = Column(Integer, primary_key=True, autoincrement=True)
    trip_id = Column(String, ForeignKey("trips.trip_id", ondelete="CASCADE"), nullable=False)
    window_index = Column(Integer, nullable=False)
    window_start_ts = Column(Integer, nullable=False)
    window_end_ts = Column(Integer, nullable=False)
    center_lat = Column(Float, nullable=True)
    center_lon = Column(Float, nullable=True)

    # --- speed ---
    speed_mean = Column(Float)
    speed_max = Column(Float)
    speed_std = Column(Float)

    # --- acceleration ---
    accel_mag_mean = Column(Float)
    accel_mag_std = Column(Float)
    accel_mag_max = Column(Float)
    accel_long_mean = Column(Float)
    accel_long_min = Column(Float)
    accel_long_max = Column(Float)
    accel_lat_max = Column(Float)

    # --- jerk ---
    jerk_mean = Column(Float)
    jerk_max = Column(Float)

    # --- gyroscope ---
    gyro_mag_mean = Column(Float)
    gyro_mag_std = Column(Float)
    gyro_z_max = Column(Float)

    # --- events ---
    harsh_brake_count = Column(Integer, default=0)
    harsh_accel_count = Column(Integer, default=0)
    harsh_corner_count = Column(Integer, default=0)
    overspeed_count = Column(Integer, default=0)

    # --- road geometry ---
    heading_change_total = Column(Float)
    bearing_std = Column(Float)
    curvature_mean = Column(Float)

    # --- novelty ---
    curve_density = Column(Float)
    curve_density_x_speed_mean = Column(Float)

    # --- prediction (Layer 5 output, stored here per Database.md Section 3) ---
    predicted_label = Column(String, nullable=True)  # LOW / MEDIUM / HIGH
    predicted_confidence = Column(Float, nullable=True)

    trip = relationship("Trip", back_populates="features")

    __table_args__ = (
        UniqueConstraint("trip_id", "window_index", name="uq_trip_window"),
    )
