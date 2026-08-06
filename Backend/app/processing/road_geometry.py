"""
Backend/app/processing/road_geometry.py
Layer 4, step 4: bearing, heading change, curvature from the GPS path.
"""
import statistics as st
from typing import List, Dict

from app.utils.geo import bearing_deg, bearing_diff_deg


def extract_road_geometry(window: List[Dict]) -> Dict:
    points = [(s["latitude"], s["longitude"]) for s in window if s["latitude"] is not None]

    if len(points) < 3:
        return {"heading_change_total": 0.0, "bearing_std": 0.0, "curvature_mean": 0.0}

    bearings = [
        bearing_deg(points[i][0], points[i][1], points[i + 1][0], points[i + 1][1])
        for i in range(len(points) - 1)
    ]

    heading_changes = (
        [abs(bearing_diff_deg(bearings[i], bearings[i + 1])) for i in range(len(bearings) - 1)]
        if len(bearings) > 1 else [0.0]
    )

    return {
        "heading_change_total": sum(heading_changes),
        "bearing_std": st.pstdev(bearings) if len(bearings) > 1 else 0.0,
        "curvature_mean": st.mean(heading_changes),
    }
