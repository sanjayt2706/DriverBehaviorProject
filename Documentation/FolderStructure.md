# FolderStructure.md

The design document specifies only `backend/ml_model/`. Everything else here is `[INFERRED]`, built to map one directory to one architecture layer so that "where does this file go" is never a judgement call.

```
driverisk/
├── docs/
│   ├── Architecture.md
│   ├── Database.md
│   ├── API.md
│   ├── FolderStructure.md
│   └── PROJECT_DESIGN_DOCUMENT.pdf
│
├── android/                          ← LAYER 1 + 2 · Student A
├── backend/                          ← LAYERS 3–7 · Student B
├── training/                         ← PIPELINE A (offline) · Student B
├── dashboard/                        ← LAYER 8 · Student A
└── data/                             ← raw drive CSVs (gitignored)
```

Four top-level modules, two owners, minimal collision surface.

---

## `android/` — Layers 1 and 2

```
android/app/src/main/java/com/driverisk/app/
├── DriveRiskApplication.kt
│
├── data/
│   ├── local/
│   │   ├── entity/
│   │   │   ├── TripEntity.kt              → trip_table
│   │   │   ├── SensorDataEntity.kt        → sensor_data_table
│   │   │   └── UploadStatusEntity.kt      → upload_status_table
│   │   ├── dao/
│   │   │   ├── TripDao.kt
│   │   │   ├── SensorDataDao.kt
│   │   │   └── UploadStatusDao.kt
│   │   └── DriveRiskDatabase.kt
│   │
│   ├── remote/                            ← LAYER 2
│   │   ├── DriveRiskApi.kt                Retrofit interface, 4 endpoints
│   │   ├── RetrofitClient.kt
│   │   └── dto/
│   │       ├── CreateTripRequest.kt
│   │       ├── UploadBatchRequest.kt
│   │       ├── SensorSampleDto.kt
│   │       ├── ProcessResponse.kt
│   │       └── TripResultResponse.kt
│   │
│   └── repository/
│       ├── TripRepository.kt
│       └── UploadRepository.kt            batching, 500 rows per call, retry
│
├── sensors/
│   ├── SensorCollector.kt                 accelerometer + gyroscope @ 50 Hz
│   ├── LocationCollector.kt               GPS @ 1 Hz
│   └── TripDetector.kt                    stop when speed ≈ 0 for N seconds
│
├── service/
│   └── TripRecordingService.kt            foreground service, survives screen-off
│
├── ui/
│   ├── home/          HomeFragment.kt · HomeViewModel.kt
│   ├── recording/     RecordingFragment.kt · RecordingViewModel.kt
│   ├── history/       HistoryFragment.kt · HistoryViewModel.kt · TripAdapter.kt
│   ├── result/        ResultFragment.kt · ResultViewModel.kt
│   └── map/           RiskMapFragment.kt · RiskMapViewModel.kt
│
└── util/
    ├── Constants.kt
    └── RiskColorMapper.kt                 LOW green · MEDIUM amber · HIGH red
```

**MVVM boundaries.** Fragments render and forward events. ViewModels hold state and call repositories. Repositories are the only classes touching Room or Retrofit. A Fragment must never see a DAO or an API interface.

**DTO rule.** Classes in `remote/dto/` mirror `API.md` field-for-field. Room entities are separate classes — never annotate one class for both Room and Retrofit.

---

## `backend/` — Layers 3 to 7

```
backend/
├── app/
│   ├── main.py                    FastAPI init, model load on startup, CORS
│   ├── config.py                  paths, window size, thresholds, w1/w2
│   ├── database.py                SQLAlchemy engine, session, WAL, FK pragma
│   │
│   ├── api/                       ← LAYER 3
│   │   ├── deps.py
│   │   ├── errors.py              error envelope from API.md
│   │   └── routes/
│   │       └── trips.py           all four endpoints
│   │
│   ├── schemas/                   ← LAYER 3 · Pydantic, mirrors API.md
│   │   ├── trip.py
│   │   ├── sensor.py
│   │   └── result.py
│   │
│   ├── models/                    ← LAYER 7 · SQLAlchemy, mirrors Database.md
│   │   ├── trip.py
│   │   ├── raw_sensor_data.py
│   │   ├── feature.py
│   │   ├── prediction.py
│   │   └── shap_explanation.py
│   │
│   ├── crud/                      ← LAYER 7 · all queries live here
│   │   ├── trip.py
│   │   ├── sensor.py
│   │   └── result.py
│   │
│   ├── processing/                ← LAYER 4 ★ THE NOVELTY
│   │   ├── preprocessing.py       clean · smooth · resample · GPS forward-fill
│   │   ├── windowing.py           5 s windows, 50% overlap
│   │   ├── features.py            the 24 window features
│   │   ├── road_geometry.py       bearing, heading change, curvature
│   │   ├── curve_density.py       ★ curves per km
│   │   └── pipeline.py            orchestrates the above in order
│   │
│   ├── ml/                        ← LAYER 5
│   │   ├── loader.py              loads .pkl + feature_list.json once at startup
│   │   ├── predictor.py           per-window LOW/MEDIUM/HIGH
│   │   └── aggregator.py          trip_score + risk_level + event counts
│   │
│   ├── explain/                   ← LAYER 6
│   │   ├── shap_explainer.py      TreeExplainer, local top 3–5
│   │   └── reason_text.py         feature name → plain-language sentence
│   │
│   └── utils/
│       ├── geo.py                 haversine, bearing
│       └── time.py
│
├── ml_model/                      ← LOCKED NAME (design document)
│   ├── best_model.pkl
│   ├── scaler.pkl
│   ├── feature_list.json
│   └── model_comparison.json
│
├── driverisk.db
├── requirements.txt
└── tests/
    ├── test_api.py
    ├── test_processing.py
    └── test_curve_density.py
```

**Where a backend file goes:**

| It does this | It belongs in |
|---|---|
| Defines a URL or handles a request | `api/routes/` |
| Validates a request or response body | `schemas/` |
| Defines a DB table | `models/` |
| Runs a query | `crud/` |
| Transforms sensor data into features | `processing/` |
| Calls `.predict()` or computes the trip score | `ml/` |
| Computes SHAP values or reason text | `explain/` |

Route functions orchestrate. They contain no maths, no feature logic, and no raw SQL.

---

## `training/` — Pipeline A, offline only

```
training/
├── src/
│   ├── step01_load_raw.py
│   ├── step02_clean.py
│   ├── step03_label.py            threshold rules + manual check
│   ├── step04_build_features.py   ← imports backend.app.processing
│   ├── step05_split_scale.py      80/20, fits and saves scaler.pkl
│   ├── step06_train_rf.py         n_estimators=200, max_depth=12
│   ├── step07_train_xgb.py        n_estimators=200, max_depth=6, lr=0.1
│   ├── step08_evaluate.py         accuracy, precision, recall, F1, CM, 5-fold CV
│   ├── step09_select_best.py      ★ the only place comparison happens
│   ├── step10_global_shap.py      global importance for the dashboard
│   └── export_artifacts.py        copies the 4 files into backend/ml_model/
│
├── notebooks/                     exploration only, never the source of truth
├── outputs/
│   ├── model_comparison.json
│   ├── confusion_matrix_rf.png
│   ├── confusion_matrix_xgb.png
│   └── shap_global_importance.png
└── requirements.txt
```

**Critical rule from `Architecture.md` §2:** `step04_build_features.py` **imports** `backend.app.processing`. It does not reimplement feature extraction. If training and runtime compute features differently, the model degrades silently and you will not find it before the viva.

---

## `dashboard/` — Layer 8

```
dashboard/
├── app.py                         Streamlit entry, sidebar navigation
├── pages/
│   ├── 1_Overview.py              trip list, score distribution
│   ├── 2_Trip_Detail.py           single trip, events, SHAP factors
│   ├── 3_Risk_Map.py              route coloured by window label
│   ├── 4_Model_Comparison.py      reads model_comparison.json
│   └── 5_Feature_Importance.py    global SHAP chart
├── db.py                          read-only connection to backend/driverisk.db
└── requirements.txt
```

The dashboard opens the SQLite file directly and never calls the API. It is **read-only** — it must never write to `driverisk.db`.

---

## `data/` — gitignored

```
data/
├── raw/           session_01_city.csv, session_02_highway.csv, …
├── processed/
└── README.md      drive log: date, driver, vehicle, route, road type
```

Keep the drive log honest. When the report asks how the dataset was collected, this file is the answer.

---

## Rules

1. One directory maps to one architecture layer. Files do not move between layers.
2. `backend/ml_model/` keeps its name — it is specified in the design document.
3. `training/` imports from `backend/`, never the reverse. The runtime backend must not depend on training code.
4. `dashboard/` depends on the DB file only, not on backend Python modules.
5. `.gitignore` must cover `data/raw/`, `*.db`, `*.pkl`, `venv/`, `.idea/`, `local.properties`, and your Google Maps API key.
