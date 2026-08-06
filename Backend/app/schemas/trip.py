"""
Backend/app/schemas/trip.py
Pydantic schemas for POST /trips. Mirrors docs/API.md Section 1 exactly.
"""
from typing import Optional
from pydantic import BaseModel, Field


class CreateTripRequest(BaseModel):
    trip_id: str = Field(..., min_length=1)
    user_id: str = Field(..., min_length=1)
    device_model: Optional[str] = None
    start_time: str  # ISO 8601 UTC


class CreateTripResponse(BaseModel):
    trip_id: str
    status: str
    created_at: str
