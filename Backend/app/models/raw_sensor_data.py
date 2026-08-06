"""
Backend/app/models/raw_sensor_data.py
SQLAlchemy model for the `raw_sensor_data` table. See docs/Database.md Section 2.
Sensor field names are locked: accel_x/y/z, gyro_x/y/z (Architecture.md Section 1).
"""
from sqlalchemy import Column, Integer, String, Float, ForeignKey, Index
from sqlalchemy.orm import relationship

from app.database import Base


class RawSensorData(Base):
    __tablename__ = "raw_sensor_data"

    id = Column(Integer, primary_key=True, autoincrement=True)
    trip_id = Column(String, ForeignKey("trips.trip_id", ondelete="CASCADE"), nullable=False)
    timestamp = Column(Integer, nullable=False)  # epoch ms
    latitude = Column(Float, nullable=True)   # GPS at 1 Hz vs IMU at 50 Hz
    longitude = Column(Float, nullable=True)
    speed = Column(Float, nullable=True)
    accel_x = Column(Float, nullable=False)
    accel_y = Column(Float, nullable=False)
    accel_z = Column(Float, nullable=False)
    gyro_x = Column(Float, nullable=False)
    gyro_y = Column(Float, nullable=False)
    gyro_z = Column(Float, nullable=False)

    trip = relationship("Trip", back_populates="raw_samples")


Index("ix_raw_sensor_trip_ts", RawSensorData.trip_id, RawSensorData.timestamp)
