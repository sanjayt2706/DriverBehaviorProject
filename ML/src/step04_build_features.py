"""
ML/src/step04_build_features.py
Pipeline A, step 4: run every discovered UAH-DriveSet trip through the
SAME feature pipeline used at runtime (Architecture.md Section 2's
shared-code rule: training imports Backend/app/processing, never
reimplements it) and attach a window-level label from step03_label.

Output: ML/outputs/dataset_features_labeled.csv - one row per window,
with all 24 model features plus trip_id/driver/road/behavior metadata
and the ground-truth `label` column.
"""
import csv
import sys
from pathlib import Path

ML_ROOT = Path(__file__).resolve().parent.parent
PROJECT_ROOT = ML_ROOT.parent
sys.path.insert(0, str(PROJECT_ROOT / "Backend"))  # exposes `app.*`, see note above

from app.processing.preprocessing import clean_and_forward_fill  # noqa: E402
from app.processing.windowing import make_windows  # noqa: E402
from app.processing.features import extract_window_features  # noqa: E402
from app.processing.road_geometry import extract_road_geometry  # noqa: E402
from app.processing.curve_density import extract_curve_density  # noqa: E402

sys.path.insert(0, str(ML_ROOT))
from step01_load_raw import discover_trips, TripSource  # noqa: E402
from step02_clean import clean_trip  # noqa: E402
from step03_label import label_windows  # noqa: E402

OUTPUT_CSV = ML_ROOT / "outputs" / "dataset_features_labeled.csv"

FEATURE_COLUMNS = [
    "speed_mean", "speed_max", "speed_std",
    "accel_mag_mean", "accel_mag_std", "accel_mag_max",
    "accel_long_mean", "accel_long_min", "accel_long_max", "accel_lat_max",
    "jerk_mean", "jerk_max",
    "gyro_mag_mean", "gyro_mag_std", "gyro_z_max",
    "harsh_brake_count", "harsh_accel_count", "harsh_corner_count", "overspeed_count",
    "heading_change_total", "bearing_std", "curvature_mean",
    "curve_density", "curve_density_x_speed_mean",
]


def build_trip_rows(trip: TripSource) -> list:
    raw_samples = clean_trip(trip.gps_file, trip.accel_file)  # UAH-specific adapter
    if len(raw_samples) < 2:
        return []

    cleaned = clean_and_forward_fill(raw_samples)  # shared with runtime
    windows = make_windows(cleaned)                 # shared with runtime
    if not windows:
        return []

    labels = label_windows(windows, trip.events_file, trip.behavior)

    rows = []
    for idx, (window, label) in enumerate(zip(windows, labels)):
        feats = extract_window_features(window)                       # shared with runtime
        geometry = extract_road_geometry(window)                       # shared with runtime
        curve = extract_curve_density(window, feats["speed_mean"])     # shared with runtime

        rows.append({
            "trip_id": trip.trip_id, "window_index": idx,
            "driver": trip.driver, "road": trip.road, "behavior": trip.behavior,
            **feats, **geometry, **curve,
            "label": label,
        })

    return rows


def main():
    trips = discover_trips()
    print(f"Discovered {len(trips)} trip folders.")

    all_rows = []
    for trip in trips:
        rows = build_trip_rows(trip)
        all_rows.extend(rows)
        print(f"  {trip.trip_id}: {len(rows)} windows")

    if not all_rows:
        raise RuntimeError("No windows produced. Check Dataset/raw/UAH-DriveSet/ contents.")

    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = ["trip_id", "window_index", "driver", "road", "behavior"] + FEATURE_COLUMNS + ["label"]
    with open(OUTPUT_CSV, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_rows)

    print(f"Wrote {len(all_rows)} labeled windows to {OUTPUT_CSV}")


if __name__ == "__main__":
    main()
