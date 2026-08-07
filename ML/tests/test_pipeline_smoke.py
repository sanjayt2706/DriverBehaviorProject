"""
ML/tests/test_pipeline_smoke.py
Regression test for steps 01-04 of the training pipeline, using a small
synthetic UAH-DriveSet-format fixture generated on the fly - so this test
runs without downloading the real ~500-minute dataset (which is large and
license-restricted, see Documentation/Dataset Specification.md).

This does NOT validate model quality (the fixture is far too small and
synthetic for that) - it only proves the UAH file-format adapter, axis
remap, upsampling, event-based labeling, and shared Backend/app/processing
integration all run without error and produce sane shapes.
"""
import math
import random
import sys
from pathlib import Path

import pytest

ML_ROOT = Path(__file__).resolve().parent.parent
PROJECT_ROOT = ML_ROOT.parent
sys.path.insert(0, str(PROJECT_ROOT / "Backend"))
sys.path.insert(0, str(ML_ROOT / "src"))

from app.processing.preprocessing import clean_and_forward_fill  # noqa: E402
from app.processing.windowing import make_windows  # noqa: E402
from app.processing.features import extract_window_features  # noqa: E402
from app.processing.road_geometry import extract_road_geometry  # noqa: E402
from app.processing.curve_density import extract_curve_density  # noqa: E402

from step01_load_raw import discover_trips  # noqa: E402
from step02_clean import clean_trip  # noqa: E402
from step03_label import label_windows  # noqa: E402


def _write_synthetic_trip(folder: Path, n_seconds=60, aggressive=False, curvy=False):
    folder.mkdir(parents=True, exist_ok=True)
    lat, lon, course = 40.4820, -3.3650, 90.0

    gps_lines = []
    for t in range(n_seconds):
        speed = 60 + (30 if aggressive else 0) + random.uniform(-5, 5)
        if curvy and t % 10 < 3:
            course += 25
        lat += 0.00005 * math.cos(math.radians(course))
        lon += 0.00005 * math.sin(math.radians(course))
        gps_lines.append(f"{t}.0 {speed:.2f} {lat:.6f} {lon:.6f} 650.0 5.0 3.0 {course:.1f} 0.0")
    (folder / "RAW_GPS.txt").write_text("\n".join(gps_lines))

    accel_lines = []
    yaw = 90.0
    for i in range(n_seconds * 10):
        t = i / 10.0
        ax = (0.5 if aggressive else 0.05) + random.uniform(-0.02, 0.02)
        ay = (0.4 if aggressive else 0.03) + random.uniform(-0.02, 0.02)
        az = 1.0 + random.uniform(-0.01, 0.01)
        if curvy and int(t) % 10 < 3:
            yaw += 2.5
        accel_lines.append(f"{t:.1f} 1 {az:.3f} {ay:.3f} {ax:.3f} {az:.3f} {ay:.3f} {ax:.3f} 0.0 0.0 {yaw:.2f}")
    (folder / "RAW_ACCELEROMETERS.txt").write_text("\n".join(accel_lines))

    events = []
    if aggressive:
        events = [f"{t}.0 1 3 {lat:.6f} {lon:.6f} 20160101120000" for t in (10, 25, 40)]
    (folder / "EVENTS_INERTIAL.txt").write_text("\n".join(events))


@pytest.fixture
def uah_fixture(tmp_path):
    root = tmp_path / "UAH-DriveSet"
    _write_synthetic_trip(root / "D1" / "route-D1-NORMAL-SECONDARY", curvy=True)
    _write_synthetic_trip(root / "D1" / "route-D1-AGGRESSIVE-MOTORWAY", aggressive=True)
    _write_synthetic_trip(root / "D2" / "route-D2-DROWSY-SECONDARY", curvy=True)
    return root


def test_discover_trips(uah_fixture):
    trips = discover_trips(uah_fixture)
    assert len(trips) == 3
    behaviors = {t.behavior for t in trips}
    assert behaviors == {"NORMAL", "AGGRESSIVE", "DROWSY"}


def test_full_adapter_pipeline(uah_fixture):
    trips = discover_trips(uah_fixture)
    total_windows = 0
    aggressive_high_count = 0

    for trip in trips:
        raw_samples = clean_trip(trip.gps_file, trip.accel_file)
        assert len(raw_samples) > 0

        # Adapted samples must expose the locked schema attributes.
        s = raw_samples[0]
        for attr in ("timestamp", "latitude", "longitude", "speed",
                     "accel_x", "accel_y", "accel_z", "gyro_x", "gyro_y", "gyro_z"):
            assert hasattr(s, attr)

        cleaned = clean_and_forward_fill(raw_samples)  # shared with runtime
        windows = make_windows(cleaned)                 # shared with runtime
        assert len(windows) > 0

        labels = label_windows(windows, trip.events_file, trip.behavior)
        assert len(labels) == len(windows)
        assert all(lbl in ("LOW", "MEDIUM", "HIGH") for lbl in labels)

        for window, label in zip(windows, labels):
            feats = extract_window_features(window)          # shared with runtime
            geometry = extract_road_geometry(window)          # shared with runtime
            curve = extract_curve_density(window, feats["speed_mean"])  # shared with runtime
            assert "curve_density" in curve
            total_windows += 1
            if trip.behavior == "AGGRESSIVE" and label == "HIGH":
                aggressive_high_count += 1

    assert total_windows > 0
    # The synthetic aggressive trip has 3 level-3 events - at least one
    # window must have picked up a HIGH label from real event evidence.
    assert aggressive_high_count > 0


def test_curvy_trip_has_nonzero_curve_density(uah_fixture):
    trips = discover_trips(uah_fixture)
    curvy_trip = next(t for t in trips if t.behavior == "NORMAL")

    raw_samples = clean_trip(curvy_trip.gps_file, curvy_trip.accel_file)
    cleaned = clean_and_forward_fill(raw_samples)
    windows = make_windows(cleaned)

    curve_densities = []
    for window in windows:
        feats = extract_window_features(window)
        curve = extract_curve_density(window, feats["speed_mean"])
        curve_densities.append(curve["curve_density"])

    assert max(curve_densities) > 0, "Curvy synthetic route should produce nonzero curve density"
