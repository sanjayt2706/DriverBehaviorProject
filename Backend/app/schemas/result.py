"""
Backend/app/schemas/result.py
Pydantic schemas for POST /trips/{trip_id}/process and GET /trips/{trip_id}/result.
Mirrors docs/API.md Sections 3 and 4.
"""
from typing import List, Optional
from pydantic import BaseModel


class ProcessResponse(BaseModel):
    trip_id: str
    status: str
    trip_score: float
    risk_level: str
    window_count: int
    processing_time_ms: int


class EventCounts(BaseModel):
    harsh_braking: int
    harsh_acceleration: int
    harsh_cornering: int
    over_speeding: int


class RiskFactor(BaseModel):
    rank: int
    feature_name: str
    shap_value: float
    feature_value: Optional[float] = None
    direction: str
    reason_text: str


class WindowSummary(BaseModel):
    window_index: int
    center_lat: Optional[float] = None
    center_lon: Optional[float] = None
    predicted_label: Optional[str] = None
    speed_mean: Optional[float] = None


class TripResultResponse(BaseModel):
    trip_id: str
    user_id: str
    start_time: str
    end_time: Optional[str] = None
    duration_s: Optional[float] = None
    distance_km: Optional[float] = None
    status: str

    trip_score: Optional[float] = None
    risk_level: Optional[str] = None
    window_count: Optional[int] = None
    pct_low: Optional[float] = None
    pct_medium: Optional[float] = None
    pct_high: Optional[float] = None

    events: Optional[EventCounts] = None
    curve_density: Optional[float] = None
    top_risk_factors: List[RiskFactor] = []
    windows: List[WindowSummary] = []

    model_name: Optional[str] = None
    processed_at: Optional[str] = None
