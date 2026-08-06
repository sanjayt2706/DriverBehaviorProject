"""
Backend/app/processing/pipeline.py
Layer 4 orchestrator. Runs on POST /trips/{trip_id}/process.
Order is locked in Architecture.md Section 4 - do not reorder without approval:
preprocessing -> windowing -> features -> road geometry -> curve density.
"""
from typing import List, Dict

from app.models.raw_sensor_data import RawSensorData
from app.processing.preprocessing import clean_and_forward_fill
from app.processing.windowing import make_windows
from app.processing.features import extract_window_features
from app.processing.road_geometry import extract_road_geometry
from app.processing.curve_density import extract_curve_density
from app.utils.geo import haversine_km


def run_pipeline(raw_samples: List[RawSensorData]) -> Dict:
    """
    raw_samples: ordered list of RawSensorData ORM rows for one trip.
    Returns {"feature_rows": [...], "distance_km": float, "duration_s": float}
    """
    cleaned = clean_and_forward_fill(raw_samples)
    windows = make_windows(cleaned)

    feature_rows: List[Dict] = []
    for idx, window in enumerate(windows):
        feats = extract_window_features(window)
        geometry = extract_road_geometry(window)
        curve = extract_curve_density(window, feats["speed_mean"])

        points = [(s["latitude"], s["longitude"]) for s in window if s["latitude"] is not None]
        center_lat = points[len(points) // 2][0] if points else None
        center_lon = points[len(points) // 2][1] if points else None

        feature_rows.append({
            "window_index": idx,
            "window_start_ts": window[0]["timestamp"],
            "window_end_ts": window[-1]["timestamp"],
            "center_lat": center_lat,
            "center_lon": center_lon,
            **feats,
            **geometry,
            **curve,
        })

    gps_points = [(s["latitude"], s["longitude"]) for s in cleaned if s["latitude"] is not None]
    distance_km = (
        sum(
            haversine_km(gps_points[i][0], gps_points[i][1], gps_points[i + 1][0], gps_points[i + 1][1])
            for i in range(len(gps_points) - 1)
        )
        if len(gps_points) > 1 else 0.0
    )

    duration_s = (
        (cleaned[-1]["timestamp"] - cleaned[0]["timestamp"]) / 1000.0
        if len(cleaned) > 1 else 0.0
    )

    return {"feature_rows": feature_rows, "distance_km": distance_km, "duration_s": duration_s}
