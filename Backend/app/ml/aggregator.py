"""
Backend/app/ml/aggregator.py
Layer 5. Trip-level aggregation. Formula is LOCKED (Architecture.md
Sections 4 and 6):

    trip_score = 100 - (w1 * pct_high + w2 * pct_medium)
    risk_level = LOW if trip_score >= 70, MEDIUM if 40-69, HIGH if < 40

Weights w1/w2 are [INFERRED] defaults; they are stored per-trip in
`predictions` so any past score stays reproducible even if the defaults
are tuned later (Section 14 of the design document is still unwritten).
"""
from typing import List, Dict

from app.config import (
    AGG_WEIGHT_W1, AGG_WEIGHT_W2,
    RISK_LOW_THRESHOLD, RISK_MEDIUM_THRESHOLD,
)


def aggregate_trip(feature_rows: List[Dict]) -> Dict:
    n = len(feature_rows)
    if n == 0:
        raise ValueError("Cannot aggregate zero windows.")

    counts = {"LOW": 0, "MEDIUM": 0, "HIGH": 0}
    for row in feature_rows:
        counts[row["predicted_label"]] += 1

    pct_low = 100 * counts["LOW"] / n
    pct_medium = 100 * counts["MEDIUM"] / n
    pct_high = 100 * counts["HIGH"] / n

    trip_score = 100 - (AGG_WEIGHT_W1 * pct_high + AGG_WEIGHT_W2 * pct_medium)
    trip_score = max(0.0, min(100.0, trip_score))

    if trip_score >= RISK_LOW_THRESHOLD:
        risk_level = "LOW"
    elif trip_score >= RISK_MEDIUM_THRESHOLD:
        risk_level = "MEDIUM"
    else:
        risk_level = "HIGH"

    return {
        "trip_score": trip_score,
        "risk_level": risk_level,
        "window_count": n,
        "pct_low": pct_low,
        "pct_medium": pct_medium,
        "pct_high": pct_high,
        "weight_w1": AGG_WEIGHT_W1,
        "weight_w2": AGG_WEIGHT_W2,
        "harsh_braking_count": sum(r["harsh_brake_count"] for r in feature_rows),
        "harsh_acceleration_count": sum(r["harsh_accel_count"] for r in feature_rows),
        "harsh_cornering_count": sum(r["harsh_corner_count"] for r in feature_rows),
        "overspeeding_count": sum(r["overspeed_count"] for r in feature_rows),
        "curve_density_trip": sum(r["curve_density"] for r in feature_rows) / n,
    }
