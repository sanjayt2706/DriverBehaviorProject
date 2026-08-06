# API.md

**Framework:** FastAPI + Pydantic
**Base URL:** `http://<host>:8000`
**Transport:** JSON over HTTP
**Client:** Android app via Retrofit + Coroutines
**Dashboard:** does **not** use this API. Streamlit reads `driverisk.db` directly.

## Frozen endpoint list

Exactly four endpoints. Adding a fifth is an API contract change and requires your explicit approval.

| # | Method | Path | Purpose |
|---|---|---|---|
| 1 | POST | `/trips` | Register a new trip |
| 2 | POST | `/trips/{trip_id}/upload` | Upload one batch of raw sensor samples |
| 3 | POST | `/trips/{trip_id}/process` | Run processing + ML + SHAP |
| 4 | GET | `/trips/{trip_id}/result` | Fetch the finished result |

Conventions: all timestamps in sample payloads are epoch **milliseconds**; all trip-level times are **ISO 8601 UTC**; `speed` is km/h; acceleration is m/s²; gyroscope is rad/s; sensor fields are `accel_x…gyro_z`; risk labels are `LOW` / `MEDIUM` / `HIGH`.

> Note on `trip.md`: that file shows the *conceptual* trip object with `samples` embedded. It is not a single request body. Trip metadata is sent by endpoint 1 and samples are sent in 500-row batches by endpoint 2, as required by D8.

---

## 1. POST `/trips`

Called when the driver presses **Start**. Registers the trip so uploads have somewhere to land.

**Request**
```json
{
  "trip_id": "trip_001",
  "user_id": "driver_001",
  "device_model": "Samsung S23 FE",
  "start_time": "2026-08-06T09:14:22Z"
}
```

| Field | Type | Required | Rule |
|---|---|---|---|
| `trip_id` | string | yes | Unique, client-generated |
| `user_id` | string | yes | Non-empty |
| `device_model` | string | no | |
| `start_time` | string | yes | ISO 8601 UTC |

**Response `201 Created`**
```json
{
  "trip_id": "trip_001",
  "status": "CREATED",
  "created_at": "2026-08-06T09:14:23Z"
}
```

**Errors:** `409` if `trip_id` already exists · `422` on validation failure.

---

## 2. POST `/trips/{trip_id}/upload`

Called repeatedly after the trip ends. **500 samples per call.**

**Request**
```json
{
  "batch_index": 0,
  "batch_count": 12,
  "end_time": "2026-08-06T09:41:05Z",
  "samples": [
    {
      "timestamp": 1722940800000,
      "latitude": 13.3409,
      "longitude": 74.7421,
      "speed": 42.5,
      "accel_x": 0.12,
      "accel_y": -0.45,
      "accel_z": 9.81,
      "gyro_x": 0.02,
      "gyro_y": -0.01,
      "gyro_z": 0.15
    }
  ]
}
```

| Field | Type | Required | Rule |
|---|---|---|---|
| `batch_index` | int | yes | 0-based |
| `batch_count` | int | yes | Total batches for this trip |
| `end_time` | string | no | Send on the final batch only |
| `samples` | array | yes | 1–500 items, rejected above 500 |

Per sample: `timestamp`, `accel_x/y/z`, `gyro_x/y/z` required. `latitude`, `longitude`, `speed` nullable — GPS is 1 Hz against 50 Hz IMU, so most rows carry no fix.

**Response `200 OK`**
```json
{
  "trip_id": "trip_001",
  "batch_index": 0,
  "received": 500,
  "total_samples": 500,
  "status": "UPLOADING"
}
```

`status` becomes `UPLOADED` once `batch_index == batch_count - 1`.

**Errors:** `404` unknown `trip_id` · `409` trip already `PROCESSED` · `422` batch exceeds 500 or a sample fails validation.

Batches may arrive out of order. Duplicate `batch_index` values are ignored rather than double-inserted, so the app can safely retry after a dropped connection.

---

## 3. POST `/trips/{trip_id}/process`

Runs the full pipeline synchronously: preprocessing → sliding window → feature extraction → road geometry → curve density → scaling → prediction → aggregation → SHAP → persist.

**Request:** empty body.

**Response `200 OK`**
```json
{
  "trip_id": "trip_001",
  "status": "PROCESSED",
  "trip_score": 68.4,
  "risk_level": "MEDIUM",
  "window_count": 312,
  "processing_time_ms": 4180
}
```

**Errors:** `404` unknown trip · `409` status is not `UPLOADED` or `PROCESSED` · `422` too few samples to form a window · `500` model or pipeline failure, trip set to `FAILED`.

Idempotent: reprocessing deletes the trip's existing `features`, `predictions` and `shap_explanations` rows before rerunning.

---

## 4. GET `/trips/{trip_id}/result`

Everything the Result screen and risk map need, in one call.

**Response `200 OK`**
```json
{
  "trip_id": "trip_001",
  "user_id": "driver_001",
  "start_time": "2026-08-06T09:14:22Z",
  "end_time": "2026-08-06T09:41:05Z",
  "duration_s": 1603.0,
  "distance_km": 18.6,
  "status": "PROCESSED",

  "trip_score": 68.4,
  "risk_level": "MEDIUM",
  "window_count": 312,
  "pct_low": 61.2,
  "pct_medium": 29.5,
  "pct_high": 9.3,

  "events": {
    "harsh_braking": 7,
    "harsh_acceleration": 4,
    "harsh_cornering": 11,
    "over_speeding": 3
  },

  "curve_density": 2.4,

  "top_risk_factors": [
    {
      "rank": 1,
      "feature_name": "harsh_corner_count",
      "shap_value": 0.184,
      "feature_value": 11.0,
      "direction": "INCREASES_RISK",
      "reason_text": "You took several corners faster than is safe for the curvature of the road."
    }
  ],

  "windows": [
    {
      "window_index": 0,
      "center_lat": 13.3409,
      "center_lon": 74.7421,
      "predicted_label": "LOW",
      "speed_mean": 31.2
    }
  ],

  "model_name": "XGBoost",
  "processed_at": "2026-08-06T09:42:10Z"
}
```

`top_risk_factors` holds 3–5 items ordered by `rank`. `windows` drives the Google Maps polyline colouring — `LOW` green, `MEDIUM` amber, `HIGH` red.

**Errors:** `404` unknown trip · `409` trip not yet processed, with `status` in the body so the app can show the right message.

---

## Error format

All errors use one shape:

```json
{
  "error": {
    "code": "TRIP_NOT_PROCESSED",
    "message": "Trip trip_001 has status UPLOADED. Call /process first.",
    "trip_id": "trip_001"
  }
}
```

| Code | HTTP | Meaning |
|---|---|---|
| `TRIP_NOT_FOUND` | 404 | Unknown `trip_id` |
| `TRIP_ALREADY_EXISTS` | 409 | Duplicate on create |
| `TRIP_NOT_PROCESSED` | 409 | Result requested too early |
| `INVALID_TRIP_STATE` | 409 | Operation illegal for current status |
| `BATCH_TOO_LARGE` | 422 | More than 500 samples |
| `INSUFFICIENT_DATA` | 422 | Fewer samples than one 5 s window |
| `VALIDATION_ERROR` | 422 | Pydantic failure |
| `PROCESSING_FAILED` | 500 | Pipeline or model error |

---

## Contract rules

1. These four endpoints, their paths, methods, field names and field types are **frozen**.
2. Sensor fields are `accel_x`, `accel_y`, `accel_z`, `gyro_x`, `gyro_y`, `gyro_z` in every layer. No aliasing between Retrofit and Pydantic.
3. Risk labels are `LOW`, `MEDIUM`, `HIGH` in every layer.
4. Retrofit DTOs and Pydantic schemas are generated from this file. If they drift, this file wins.
5. Any change here requires a stated reason and your approval first.
