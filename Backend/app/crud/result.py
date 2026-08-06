"""
Backend/app/crud/result.py
Builds the aggregate response for GET /trips/{trip_id}/result (API.md Section 4),
and persists the outputs of the /process pipeline into features, predictions,
and shap_explanations.
"""
from typing import List, Dict
from sqlalchemy.orm import Session

from app.models.trip import Trip
from app.models.feature import Feature
from app.models.prediction import Prediction
from app.models.shap_explanation import ShapExplanation
from app.utils.time import utc_now_iso


def clear_previous_results(db: Session, trip_id: str) -> None:
    """Makes /process idempotent (Architecture.md Section 5)."""
    db.query(ShapExplanation).filter(ShapExplanation.trip_id == trip_id).delete()
    db.query(Prediction).filter(Prediction.trip_id == trip_id).delete()
    db.query(Feature).filter(Feature.trip_id == trip_id).delete()
    db.commit()


def save_features(db: Session, trip_id: str, feature_rows: List[Dict]) -> int:
    rows = [{**row, "trip_id": trip_id} for row in feature_rows]
    db.bulk_insert_mappings(Feature, rows)
    db.commit()
    return len(rows)


def save_prediction(db: Session, trip_id: str, prediction: Dict) -> Prediction:
    row = Prediction(trip_id=trip_id, created_at=utc_now_iso(), **prediction)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def save_shap_explanations(db: Session, trip_id: str, factors: List[Dict]) -> int:
    rows = [{**f, "trip_id": trip_id} for f in factors]
    db.bulk_insert_mappings(ShapExplanation, rows)
    db.commit()
    return len(rows)


def build_result(db: Session, trip: Trip) -> Dict:
    prediction = db.query(Prediction).filter(Prediction.trip_id == trip.trip_id).first()
    factors = (
        db.query(ShapExplanation)
        .filter(ShapExplanation.trip_id == trip.trip_id)
        .order_by(ShapExplanation.rank.asc())
        .all()
    )
    windows = (
        db.query(Feature)
        .filter(Feature.trip_id == trip.trip_id)
        .order_by(Feature.window_index.asc())
        .all()
    )

    result: Dict = {
        "trip_id": trip.trip_id,
        "user_id": trip.user_id,
        "start_time": trip.start_time,
        "end_time": trip.end_time,
        "duration_s": trip.duration_s,
        "distance_km": trip.distance_km,
        "status": trip.status,
    }

    if prediction:
        result.update({
            "trip_score": prediction.trip_score,
            "risk_level": prediction.risk_level,
            "window_count": prediction.window_count,
            "pct_low": prediction.pct_low,
            "pct_medium": prediction.pct_medium,
            "pct_high": prediction.pct_high,
            "events": {
                "harsh_braking": prediction.harsh_braking_count,
                "harsh_acceleration": prediction.harsh_acceleration_count,
                "harsh_cornering": prediction.harsh_cornering_count,
                "over_speeding": prediction.overspeeding_count,
            },
            "curve_density": prediction.curve_density_trip,
            "model_name": prediction.model_name,
            "processed_at": trip.processed_at,
        })

    result["top_risk_factors"] = [
        {
            "rank": f.rank,
            "feature_name": f.feature_name,
            "shap_value": f.shap_value,
            "feature_value": f.feature_value,
            "direction": f.direction,
            "reason_text": f.reason_text,
        }
        for f in factors
    ]

    result["windows"] = [
        {
            "window_index": w.window_index,
            "center_lat": w.center_lat,
            "center_lon": w.center_lon,
            "predicted_label": w.predicted_label,
            "speed_mean": w.speed_mean,
        }
        for w in windows
    ]

    return result
