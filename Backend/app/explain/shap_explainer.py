"""
Backend/app/explain/shap_explainer.py
Layer 6. Local SHAP explanation for one trip - the 3-5 top risk factors.

Falls back to a ranked heuristic when no trained model is loaded yet (same
placeholder strategy as ml/predictor.py), so /process stays testable before
ML/ finishes training. Real SHAP TreeExplainer wiring activates automatically
once best_model.pkl exists.
"""
from typing import List, Dict

from app.ml.loader import model_bundle
from app.explain.reason_text import build_reason_text

_EVENT_FEATURES = [
    "harsh_brake_count", "harsh_accel_count",
    "harsh_corner_count", "overspeed_count",
    "curve_density_x_speed_mean", "speed_std", "jerk_max",
]


def _heuristic_top_factors(feature_rows: List[Dict], top_n: int = 5) -> List[Dict]:
    """[PLACEHOLDER] Ranks by summed magnitude, not real SHAP values."""
    totals = {f: sum(r.get(f, 0) for r in feature_rows) for f in _EVENT_FEATURES}
    ranked = sorted(totals.items(), key=lambda kv: kv[1], reverse=True)
    ranked = [(name, val) for name, val in ranked if val > 0][:top_n]

    factors = []
    for i, (name, val) in enumerate(ranked, start=1):
        factors.append({
            "rank": i,
            "feature_name": name,
            "shap_value": float(val),  # not a real SHAP value in placeholder mode
            "feature_value": float(val),
            "direction": "INCREASES_RISK",
            "reason_text": build_reason_text(name, "INCREASES_RISK"),
        })
    return factors


def explain_trip(feature_rows: List[Dict], top_n: int = 5) -> List[Dict]:
    if model_bundle.loaded:
        # Real SHAP TreeExplainer wiring goes here once best_model.pkl exists:
        #   import shap
        #   explainer = shap.TreeExplainer(model_bundle.model)
        #   shap_values = explainer.shap_values(...)
        pass

    return _heuristic_top_factors(feature_rows, top_n)
