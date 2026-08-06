# Architecture.md

**Project:** AI-Based Smartphone Driver Behaviour Analysis and Risk Prediction System using Explainable Machine Learning
**Status:** Derived from `PROJECT_DESIGN_DOCUMENT.md` Section 1 + Architecture Reference D1–D8
**Rule:** This file restates the approved architecture. It does not introduce new architecture. Items I had to infer are tagged `[INFERRED]` and require your approval before they become binding.

---

## 1. Locked project decisions

| Decision | Value | Source |
|---|---|---|
| Hardware | Smartphone only. No OBD-II, no external device. | Section 1.1 |
| Prediction location | Server-side only. No on-device ML. | Section 1.8 |
| Models | Random Forest and XGBoost. No deep learning. | Section 1.8 |
| Model comparison | Offline, training-time only. Exactly one model runs at runtime. | Section 1.3 |
| Explainability | SHAP TreeExplainer, local + global. | D6 |
| Database | Single SQLite file `driverisk.db`. | D7 |
| Dashboard access | Streamlit reads `driverisk.db` directly, not through the API. | D8 |
| Team | 2 students. A = Android + Maps + Streamlit. B = Backend + DB + ML + SHAP. | Section 1.11 |
| Duration | MVP 4 days, full project 15 days. | Header |

### Naming conventions locked in this revision

| Item | Canonical form | Applies to |
|---|---|---|
| Sensor axes | `accel_x`, `accel_y`, `accel_z`, `gyro_x`, `gyro_y`, `gyro_z` | Room entities, Retrofit DTOs, Pydantic schemas, SQLAlchemy models, training CSVs |
| Risk labels | `LOW`, `MEDIUM`, `HIGH` | Window-level prediction, trip-level `risk_level`, training labels, dashboard |

> Diagram D4 in the design document shows `ax, ay, az, gx, gy, gz` and the label set `SAFE / MODERATE / RISKY`. Both are **superseded** by the table above. When D4 is redrawn for the report it must be updated to match, or the report and the code will disagree at the viva.

---

## 2. The two pipelines (D2)

The system is two separate pipelines that meet at exactly one place: the model artifact files.

```
PIPELINE A — TRAINING (offline, our laptop)     PIPELINE B — PREDICTION (runtime, server)
─────────────────────────────────────────       ─────────────────────────────────────────
Driving dataset (CSV)                            Android app (accel, gyro, GPS)
        ↓                                                ↓
Data cleaning                                    FastAPI backend (validate, store raw)
        ↓                                                ↓
Sliding window                                   Preprocessing
        ↓                                                ↓
Feature extraction                               Sliding window
        ↓                                                ↓
Road geometry                                    Feature extraction
        ↓                                                ↓
★ Curve density                                  Road geometry
        ↓                                                ↓
Train RF + XGBoost, compare, select              ★ Curve density
        ↓                                                ↓
best_model.pkl, scaler.pkl,                      Load model → predict → aggregate
feature_list.json, model_comparison.json  ─────► SHAP explain → store → serve
```

**Why they are separate:** the runtime backend loads one model and stays small; the model can be retrained without touching backend code; running both models at prediction time would be slow and methodologically wrong.

### The shared-code rule `[INFERRED]`

Both pipelines must compute features identically, or the model sees different inputs at training and prediction time and accuracy collapses silently.

**Rule:** `backend/app/processing/` is the single implementation of preprocessing, windowing, feature extraction, road geometry and curve density. The training pipeline in `training/` **imports** these modules. It never reimplements them.

This is not stated in the design document but is required for the design to work. Flagged for your approval.

---

## 3. Layered architecture (D3)

| Layer | Name | Technology | Owner |
|---|---|---|---|
| 1 | Presentation | Android, Kotlin, MVVM, Google Maps SDK | Student A |
| 2 | Communication | Retrofit, Coroutines, REST/JSON over HTTP | A + B |
| 3 | Backend | FastAPI, Pydantic validation, API routes | Student B |
| 4 | **Processing ★** | Preprocessing → Windowing → Features → Road geometry → **Curve density** | Student B |
| 5 | Machine Learning | Scikit-Learn, XGBoost, loaded `.pkl` artifacts | Student B |
| 6 | Explainability | SHAP TreeExplainer | Student B |
| 7 | Data | SQLAlchemy + SQLite | Student B |
| 8 | Visualization | Streamlit dashboard | Student A |

Layer 4 is the project's novelty and the part that must not be rushed.

---

## 4. Layer responsibilities

### Layer 1 — Presentation (Android)
Screens: Home, Recording, Trip History, Result, Risk Map.
Records accelerometer and gyroscope at 50 Hz and GPS at 1 Hz. Detects trip start (manual Start button) and trip end (manual Stop, or speed ≈ 0 for N seconds). Buffers everything in Room so the app works fully offline. Uploads in batches when a network is available.

The app performs **no** feature extraction and **no** prediction. It records, stores, uploads, and displays.

### Layer 2 — Communication
Retrofit + Coroutines. JSON over HTTP. Sensor samples are uploaded in batches of **500 rows per call**. The API contract is frozen in `API.md`.

### Layer 3 — Backend (FastAPI)
Four endpoints only:
- `POST /trips` — register a trip
- `POST /trips/{trip_id}/upload` — receive a batch of raw samples
- `POST /trips/{trip_id}/process` — run the full processing + ML + SHAP pipeline
- `GET /trips/{trip_id}/result` — return the finished result

Every request and response is validated by Pydantic. The backend orchestrates; it contains no algorithm logic of its own.

### Layer 4 — Processing ★
Executed in order on `POST /trips/{trip_id}/process`:

1. **Preprocessing** — clean, smooth, resample. Drop rows with missing GPS or impossible speeds.
2. **Sliding window** — 5 second windows, 50% overlap.
3. **Feature extraction** — statistical and behavioural features per window.
4. **Road geometry** — bearing and curvature from the GPS path.
5. **★ Curve density** — curves per km, the headline novel feature.
6. **Interaction feature** — `curve_density × speed_mean`.
7. **Scaling** — `StandardScaler` loaded from `scaler.pkl`. Never re-fitted at runtime.

Output: one row per window written to the `features` table.

### Layer 5 — Machine Learning
At server startup, load `best_model.pkl`, `scaler.pkl` and `feature_list.json` into memory once. `feature_list.json` is authoritative for both the set and the **order** of columns fed to the model.

Predicts `LOW / MEDIUM / HIGH` per window, then aggregates to a trip score:

```
trip_score = 100 − ( w1 · %HIGH_windows + w2 · %MEDIUM_windows )

risk_level = LOW     if trip_score ≥ 70
             MEDIUM  if 40 ≤ trip_score < 70
             HIGH    if trip_score < 40
```

`w1` and `w2` values are not yet fixed in the design document (Section 14 is unwritten). Proposed: `w1 = 1.0`, `w2 = 0.4`. `[INFERRED]` — the weights actually used are stored per-trip in the `predictions` table so any result can be reproduced.

### Layer 6 — Explainability
SHAP `TreeExplainer` on the loaded model.
- **Local** — top 3–5 risk factors for this specific trip, converted to plain-language reason text.
- **Global** — overall feature importance bar chart for the dashboard.

### Layer 7 — Data
SQLAlchemy over one SQLite file, `driverisk.db`. Five tables, fully specified in `Database.md`:

| # | Table | Written by | Read by |
|---|---|---|---|
| 1 | `trips` | Backend on trip creation | App, Dashboard |
| 2 | `raw_sensor_data` | Backend on upload | Processing layer |
| 3 | `features` | Processing layer | ML layer, Dashboard |
| 4 | `predictions` | ML layer | App, Dashboard |
| 5 | `shap_explanations` | Explainability layer | App, Dashboard |

### Layer 8 — Visualization
Streamlit, reading `driverisk.db` directly. Shows driver analytics, risk map, model comparison (from `model_comparison.json`), and the global SHAP feature importance chart.

---

## 5. Runtime request flow

```
App: Start pressed
  → POST /trips                       → row in trips (status = CREATED)
App: records to Room while driving
App: Stop pressed
  → POST /trips/{id}/upload  × N      → rows in raw_sensor_data (status = UPLOADING → UPLOADED)
  → POST /trips/{id}/process          → status = PROCESSING
        preprocessing → windowing → features → road geometry → curve density
        → features table
        → model.predict per window   → per-window label
        → aggregate                  → predictions table
        → SHAP                       → shap_explanations table
                                      → status = PROCESSED
  → GET /trips/{id}/result            → Result screen + risk map
```

Processing is **synchronous** `[INFERRED]`. With 4–6 hours of total data and one trip processed at a time, a background job queue is unnecessary complexity for a 15-day build.

---

## 6. Training pipeline steps (D5)

| Step | Action |
|---|---|
| 1 | Input raw CSVs from data-collection drives |
| 2–3 | Cleaning, preprocessing |
| 4 | Sliding window (5 s, 50% overlap) |
| 5 | Feature extraction |
| 6 | Road geometry + ★ curve density |
| 7 | Interaction feature `curve_density × speed_mean`; `StandardScaler`; save `feature_list.json` |
| 8 | Split 80% train / 20% test |
| 9 | Train RF (`n_estimators=200`, `max_depth=12`) and XGBoost (`n_estimators=200`, `max_depth=6`, `learning_rate=0.1`) |
| 10 | Evaluate: accuracy, precision, recall, F1, confusion matrix, 5-fold CV → `model_comparison.json` |
| 11 | **Select the higher F1 model. This is the only place comparison happens.** |
| 12 | Save `best_model.pkl`, `scaler.pkl`, `feature_list.json`, `model_comparison.json` → copy into `backend/ml_model/` |

Dataset targets: 8–12 sessions, 4–6 hours total, 2 drivers, 1–2 vehicles, covering city / highway / curvy roads. Curvy roads are mandatory — without them the curve density feature has no variance and the novelty claim fails.

---

## 7. Deployment (D7)

Android APK on the phone → HTTP/JSON over Wi-Fi or mobile data → FastAPI on `uvicorn`, port 8000, running on a laptop or free hosting. `driverisk.db` and `backend/ml_model/` sit beside the backend. Streamlit runs on the same machine and opens the same DB file.

No AWS, no GCP, no containers.

---

## 8. Out of scope

Real-time driving warnings · on-device ML · deep learning (LSTM/CNN) · OBD-II · insurance premium calculation · multi-user fleet roles · iOS · cloud deployment.

> **Open conflict:** `ReportPhase1.pdf` submitted to the college promises **K-Means driver profiling** and an owner-monitoring feature. Neither is in the design document's in-scope list. This must be resolved before the viva — either add a scoped K-Means clustering panel to the Streamlit dashboard, or add an explicit scope-change note to Section 1. Awaiting your decision.

---

## 9. Change control

Changing anything in Sections 1, 3, 4, 5 or 7 of this file is an architecture change. It requires an explicit instruction from you, and the reason must be stated before the change is made.
