"""
Backend/app/explain/reason_text.py
Layer 6. Converts a feature name + direction into a plain-language sentence
for the app's Result screen (Architecture.md Section 4, Layer 6).
"""

_TEMPLATES = {
    "harsh_brake_count": "You braked harshly several times during this trip.",
    "harsh_accel_count": "You accelerated harshly several times during this trip.",
    "harsh_corner_count": "You took corners faster than is safe for the road's curvature.",
    "overspeed_count": "You drove over the speed limit for part of this trip.",
    "curve_density": "This trip covered an unusually curvy road.",
    "curve_density_x_speed_mean": "You drove fast on stretches with many curves.",
    "speed_std": "Your speed varied a lot during this trip.",
    "jerk_max": "Your driving included some abrupt, jerky movements.",
}

_DEFAULT_INCREASE = "This factor increased your risk score."
_DEFAULT_DECREASE = "This factor decreased your risk score."


def build_reason_text(feature_name: str, direction: str) -> str:
    if feature_name in _TEMPLATES:
        return _TEMPLATES[feature_name]
    return _DEFAULT_INCREASE if direction == "INCREASES_RISK" else _DEFAULT_DECREASE
