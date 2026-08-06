"""
Backend/app/schemas/sensor.py
Pydantic schemas for POST /trips/{trip_id}/upload. Mirrors docs/API.md Section 2.
Sensor field names are locked: accel_x/y/z, gyro_x/y/z (Architecture.md Section 1).
"""
from typing import List, Optional
from pydantic import BaseModel, Field


class SensorSample(BaseModel):
    timestamp: int  # epoch ms
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    speed: Optional[float] = None
    accel_x: float
    accel_y: float
    accel_z: float
    gyro_x: float
    gyro_y: float
    gyro_z: float


class UploadBatchRequest(BaseModel):
    batch_index: int = Field(..., ge=0)
    batch_count: int = Field(..., ge=1)
    end_time: Optional[str] = None
    samples: List[SensorSample] = Field(..., min_length=1, max_length=500)


class UploadBatchResponse(BaseModel):
    trip_id: str
    batch_index: int
    received: int
    total_samples: int
    status: str
