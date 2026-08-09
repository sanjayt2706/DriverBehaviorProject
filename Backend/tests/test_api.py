"""
Backend/tests/test_api.py
End-to-end smoke test for the 4 locked endpoints, using the placeholder
heuristic predictor (no trained model required). Generates a short synthetic
trip: mostly straight, with one sharp turn, to exercise curve density and
the harsh-cornering event.
"""
from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture(scope="module")
def client():
    # TestClient must be used as a context manager for startup events
    # (init_db, model_bundle.load) to run.
    with TestClient(app) as c:
        yield c


def _synthetic_samples(n=300, start_ts=1_722_940_800_000):
    """~6 seconds at 50 Hz along a path with one sharp turn partway through."""
    samples = []
    lat, lon = 13.3409, 74.7421
    for i in range(n):
        ts = start_ts + i * 20  # 50 Hz -> 20 ms per sample
        turning = 100 <= i <= 130
        lat += 0.00002
        lon += -0.00003 if turning else 0.00003
        samples.append({
            "timestamp": ts,
            "latitude": lat if i % 50 == 0 else None,  # GPS ~1 Hz
            "longitude": lon if i % 50 == 0 else None,
            "speed": 40.0 if i % 50 == 0 else None,
            "accel_x": 4.0 if turning else 0.1,
            "accel_y": 0.5,
            "accel_z": 9.81,
            "gyro_x": 0.0,
            "gyro_y": 0.0,
            "gyro_z": 0.5 if turning else 0.02,
        })
    return samples


def test_full_round_trip(client):
    trip_id = "test_trip_001"

    r = client.post("/trips", json={
        "trip_id": trip_id,
        "user_id": "test_driver",
        "device_model": "TestPhone",
        "start_time": "2026-08-06T09:00:00Z",
    })
    assert r.status_code == 201
    assert r.json()["status"] == "CREATED"

    samples = _synthetic_samples()
    r = client.post(f"/trips/{trip_id}/upload", json={
        "batch_index": 0,
        "batch_count": 1,
        "end_time": "2026-08-06T09:00:06Z",
        "samples": samples,
    })
    assert r.status_code == 200
    assert r.json()["status"] == "UPLOADED"

    r = client.post(f"/trips/{trip_id}/process")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "PROCESSED"
    assert body["risk_level"] in ("LOW", "MEDIUM", "HIGH")

    r = client.get(f"/trips/{trip_id}/result")
    assert r.status_code == 200
    result = r.json()
    assert result["trip_score"] is not None
    assert len(result["windows"]) > 0
    assert result["curve_density"] is not None


def test_duplicate_batch_index_not_double_inserted(client):
    """API.md: 'Duplicate batch_index values are ignored rather than
    double-inserted, so the app can safely retry after a dropped connection.'
    Simulates the app resending batch_index=0 after never seeing the
    first response."""
    trip_id = "test_trip_dup_batch"
    client.post("/trips", json={
        "trip_id": trip_id, "user_id": "test_driver", "start_time": "2026-08-06T09:00:00Z",
    })

    payload = {
        "batch_index": 0,
        "batch_count": 1,
        "end_time": "2026-08-06T09:00:06Z",
        "samples": _synthetic_samples(n=100),
    }

    r1 = client.post(f"/trips/{trip_id}/upload", json=payload)
    assert r1.status_code == 200
    assert r1.json()["total_samples"] == 100

    r2 = client.post(f"/trips/{trip_id}/upload", json=payload)
    assert r2.status_code == 200
    assert r2.json()["received"] == 100  # looks like a normal success to the client
    assert r2.json()["total_samples"] == 100  # but nothing was actually re-inserted


def test_concurrent_duplicate_batch_upload_not_double_inserted(client):
    """
    The sequential dup test above sends the retry only after the first
    request's response has fully returned, so it never actually overlaps
    the two requests - it can't catch a check-then-act race where both
    requests see "not yet received" before either commits. This fires both
    requests from separate threads at (approximately) the same time, which
    is what a real client retrying because it never saw a response --
    rather than because it saw a definite failure -- looks like.
    """
    trip_id = "test_trip_concurrent_dup_batch"
    client.post("/trips", json={
        "trip_id": trip_id, "user_id": "test_driver", "start_time": "2026-08-06T09:00:00Z",
    })

    payload = {
        "batch_index": 0,
        "batch_count": 1,
        "end_time": "2026-08-06T09:00:06Z",
        "samples": _synthetic_samples(n=100),
    }

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [
            pool.submit(client.post, f"/trips/{trip_id}/upload", json=payload)
            for _ in range(2)
        ]
        responses = [f.result() for f in futures]

    assert all(r.status_code == 200 for r in responses)
    final_total = client.post(f"/trips/{trip_id}/upload", json=payload).json()["total_samples"]
    assert final_total == 100  # exactly one of the two concurrent requests may have inserted


def test_unknown_trip_404(client):
    r = client.get("/trips/does_not_exist/result")
    assert r.status_code == 404
    assert r.json()["detail"]["error"]["code"] == "TRIP_NOT_FOUND"


def test_duplicate_trip_409(client):
    trip_id = "test_trip_dup"
    client.post("/trips", json={
        "trip_id": trip_id, "user_id": "u", "start_time": "2026-08-06T09:00:00Z",
    })
    r = client.post("/trips", json={
        "trip_id": trip_id, "user_id": "u", "start_time": "2026-08-06T09:00:00Z",
    })
    assert r.status_code == 409


def test_result_before_process_409(client):
    trip_id = "test_trip_early_result"
    client.post("/trips", json={
        "trip_id": trip_id, "user_id": "u", "start_time": "2026-08-06T09:00:00Z",
    })
    r = client.get(f"/trips/{trip_id}/result")
    assert r.status_code == 409
    assert r.json()["detail"]["error"]["code"] == "TRIP_NOT_PROCESSED"
