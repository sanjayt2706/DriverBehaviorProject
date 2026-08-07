"""
Backend/app/explain/reason_text.py
Layer 6. Converts a feature name + direction into a plain-language sentence
for the app's Result screen (Architecture.md Section 4, Layer 6).
"""

_TEMPLATES = {
    "harsh_brake_count": (
        "You braked harshly several times during this trip.",
        "Your braking stayed smooth throughout this trip.",
    ),
    "harsh_accel_count": (
        "You accelerated harshly several times during this trip.",
        "Your acceleration stayed smooth throughout this trip.",
    ),
    "harsh_corner_count": (
        "You took corners faster than is safe for the road's curvature.",
        "You took corners at a safe speed for the road's curvature.",
    ),
    "overspeed_count": (
        "You drove over the speed limit for part of this trip.",
        "You stayed within the speed limit throughout this trip.",
    ),
    "curve_density": (
        "This trip covered an unusually curvy road.",
        "This trip's road was relatively straight, with few curves.",
    ),
    "curve_density_x_speed_mean": (
        "You drove fast on stretches with many curves.",
        "You slowed down appropriately on curvy stretches.",
    ),
    "speed_std": (
        "Your speed varied a lot during this trip.",
        "You maintained a steady speed during this trip.",
    ),
    "jerk_max": (
        "Your driving included some abrupt, jerky movements.",
        "Your driving was smooth, without abrupt movements.",
    ),
}

_DEFAULT_INCREASE = "This factor increased your risk score."
_DEFAULT_DECREASE = "This factor decreased your risk score."


def build_reason_text(feature_name: str, direction: str) -> str:
    increases = direction == "INCREASES_RISK"
    if feature_name in _TEMPLATES:
        increase_text, decrease_text = _TEMPLATES[feature_name]
        return increase_text if increases else decrease_text
    return _DEFAULT_INCREASE if increases else _DEFAULT_DECREASE
