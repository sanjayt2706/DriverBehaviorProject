"""
Backend/app/explain/shap_explainer.py
Layer 6. Local SHAP explanation for one trip - the 3-5 top risk factors.

Falls back to a ranked heuristic when no trained model is loaded yet (same
placeholder strategy as ml/predictor.py), so /process stays testable before
ML/ finishes training. Real SHAP TreeExplainer wiring activates automatically
once best_model.pkl exists.
"""
from typing import List, Dict

from app.config import AGG_WEIGHT_W1, AGG_WEIGHT_W2
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


def _shap_top_factors(feature_rows: List[Dict], top_n: int = 5) -> List[Dict]:
    """
    Real local SHAP explanation, averaged across the trip's windows.

    TreeExplainer needs the raw sklearn/xgboost estimator, not the
    LabelDecodingClassifier wrapper (see app/ml/model_wrapper.py) - same
    unwrap ML/src/step10_global_shap_fixed.py needs for global importance.

    Each window gets one SHAP value per feature per class (LOW/MEDIUM/HIGH).
    A feature's contribution to *this window's risk* is defined the same way
    trip_score itself is defined (ml/aggregator.py): the HIGH-class SHAP
    value weighted by w1 plus the MEDIUM-class SHAP value weighted by w2.
    That keeps "risk factor" consistent with what trip_score measures,
    instead of depending on which class happened to win that window.
    """
    import shap

    raw_model = model_bundle.model.model  # unwrap LabelDecodingClassifier
    explainer = shap.TreeExplainer(raw_model)

    feature_list = model_bundle.feature_list
    X = [[row[f] for f in feature_list] for row in feature_rows]
    X_scaled = model_bundle.scaler.transform(X)

    values = explainer(X_scaled).values.tolist()  # [window][feature][class]

    classes = list(model_bundle.model.classes_)
    high_idx = classes.index("HIGH")
    medium_idx = classes.index("MEDIUM")

    n_features = len(feature_list)
    n_windows = len(feature_rows)
    signed_sum = [0.0] * n_features
    abs_sum = [0.0] * n_features
    for window in values:
        for f in range(n_features):
            risk = AGG_WEIGHT_W1 * window[f][high_idx] + AGG_WEIGHT_W2 * window[f][medium_idx]
            signed_sum[f] += risk
            abs_sum[f] += abs(risk)

    ranked = sorted(range(n_features), key=lambda f: abs_sum[f], reverse=True)[:top_n]

    factors = []
    for rank, idx in enumerate(ranked, start=1):
        name = feature_list[idx]
        signed_val = signed_sum[idx] / n_windows
        direction = "INCREASES_RISK" if signed_val >= 0 else "DECREASES_RISK"
        factors.append({
            "rank": rank,
            "feature_name": name,
            "shap_value": signed_val,
            "feature_value": sum(row.get(name, 0.0) for row in feature_rows) / n_windows,
            "direction": direction,
            "reason_text": build_reason_text(name, direction),
        })
    return factors


def explain_trip(feature_rows: List[Dict], top_n: int = 5) -> List[Dict]:
    if model_bundle.loaded:
        return _shap_top_factors(feature_rows, top_n)

    return _heuristic_top_factors(feature_rows, top_n)
