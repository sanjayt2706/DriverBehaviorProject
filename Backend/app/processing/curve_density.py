"""
Backend/app/processing/curve_density.py
Layer 4, step 5 (the novel feature, D1): curves per km for a window.
A "curve" is a heading change over CURVE_HEADING_CHANGE_DEG within the window
(Architecture.md D1). The threshold is [INFERRED] - tune once real curvy-road
drives are collected (Architecture.md Section 6 dataset plan).
"""
from typing import List, Dict

from app.config import CURVE_HEADING_CHANGE_DEG
from app.utils.geo import haversine_km, bearing_deg, bearing_diff_deg


def extract_curve_density(window: List[Dict], speed_mean: float) -> Dict:
    points = [(s["latitude"], s["longitude"]) for s in window if s["latitude"] is not None]

    if len(points) < 3:
        return {"curve_density": 0.0, "curve_density_x_speed_mean": 0.0}

    distance_km = sum(
        haversine_km(points[i][0], points[i][1], points[i + 1][0], points[i + 1][1])
        for i in range(len(points) - 1)
    )

    bearings = [
        bearing_deg(points[i][0], points[i][1], points[i + 1][0], points[i + 1][1])
        for i in range(len(points) - 1)
    ]
    curve_count = sum(
        1 for i in range(len(bearings) - 1)
        if abs(bearing_diff_deg(bearings[i], bearings[i + 1])) >= CURVE_HEADING_CHANGE_DEG
    )

    curve_density = curve_count / distance_km if distance_km > 0 else 0.0

    return {
        "curve_density": curve_density,
        "curve_density_x_speed_mean": curve_density * speed_mean,
    }
