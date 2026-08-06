"""
Backend/app/ml/predictor.py
Layer 5. Per-window LOW/MEDIUM/HIGH prediction.

Falls back to a transparent, rule-based heuristic when no trained model is
loaded yet, so /process is testable before ML/ finishes training (Days 1-4).
Real model prediction takes over automatically once best_model.pkl exists -
no code change needed here.
"""
from typing import Dict, Tuple

from app.ml.loader import model_bundle


def _heuristic_label(feature_row: Dict) -> Tuple[str, float]:
    """[PLACEHOLDER] Simple threshold rule, not the trained model."""
    score = 0
    score += feature_row.get("harsh_brake_count", 0)
    score += feature_row.get("harsh_accel_count", 0)
    score += feature_row.get("harsh_corner_count", 0)
    score += feature_row.get("overspeed_count", 0)

    if score == 0:
        return "LOW", 0.6
    elif score <= 2:
        return "MEDIUM", 0.55
    else:
        return "HIGH", 0.6


def predict_window(feature_row: Dict) -> Tuple[str, float]:
    if model_bundle.loaded:
        x = [[feature_row[f] for f in model_bundle.feature_list]]
        x_scaled = model_bundle.scaler.transform(x)
        label = model_bundle.model.predict(x_scaled)[0]
        proba = model_bundle.model.predict_proba(x_scaled)[0]
        confidence = float(max(proba))
        return str(label), confidence

    return _heuristic_label(feature_row)
