# PROJECT_STATUS.md

**Project:** AI-Based Smartphone Driver Behaviour Analysis and Risk Prediction System using Explainable Machine Learning
**Generated:** 2026-08-07, by direct inspection of every file in `Documentation/`, `Backend/`, `ML/`, and `Android/` (not from memory or prior summaries).
**Scope note:** This document is a snapshot. The project is being actively worked on; re-verify before relying on any specific claim below more than a few days old.

---

## 1. Project architecture

Locked in `Documentation/Architecture.md` (changes to its Sections 1/3/4/5/7 require an explicit instruction with a stated reason). Two people, eight layers, two pipelines that meet at one set of files.

**Team split:** Student A = Android + Google Maps + Streamlit dashboard (Layers 1, 2, 8). Student B = Backend + DB + ML + SHAP (Layers 3–7).

**The two pipelines** (meet at the model artifact files):

```
PIPELINE A — TRAINING (offline)                  PIPELINE B — PREDICTION (runtime)
────────────────────────────────                 ──────────────────────────────────
Dataset (UAH-DriveSet CSVs)                       Android app (accel, gyro, GPS)
   ↓ clean/adapt (dataset-specific)                   ↓
Backend/app/processing/ (SHARED) ────────────────→Backend/app/processing/ (SHARED)
   preprocessing → windowing → features →             preprocessing → windowing → features →
   road_geometry → ★curve_density                     road_geometry → ★curve_density
   ↓                                                   ↓
Train RF + XGBoost, compare, select               Load best_model.pkl → predict → aggregate
   ↓                                                   ↓
best_model.pkl, scaler.pkl,                       SHAP explain → persist to driverisk.db →
feature_list.json, model_comparison.json ────────→serve via API
```

**Shared-code rule (the load-bearing constraint of the whole design):** `Backend/app/processing/` is the *only* implementation of preprocessing/windowing/features/road-geometry/curve-density. The training pipeline (`ML/`) imports it; it never reimplements it. Verified true by inspection — `ML/src/step04_build_features.py` imports directly from `app.processing.*`.

**Locked technology choices:**
| Decision | Value |
|---|---|
| Sensing | Smartphone only (accel + gyro @ 50 Hz, GPS @ 1 Hz). No OBD-II. |
| Prediction | Server-side only. No on-device ML. |
| Models | Random Forest and XGBoost only. No deep learning. Exactly one runs at runtime. |
| Explainability | SHAP `TreeExplainer`, local (per-trip) + global (dashboard). |
| Database | Single SQLite file `driverisk.db`, 5 tables, WAL mode. |
| Dashboard | Streamlit, reads `driverisk.db` directly — never calls the API. |
| API | Exactly 4 REST endpoints, frozen field names, JSON. |
| Risk labels | `LOW` / `MEDIUM` / `HIGH` everywhere (an older diagram's `SAFE/MODERATE/RISKY` is superseded). |

**Trip scoring formula (locked):** `trip_score = 100 − (w1·%HIGH_windows + w2·%MEDIUM_windows)`, `w1=1.0`, `w2=0.4` (`Backend/app/config.py`). `risk_level` = LOW ≥70, MEDIUM 40–69, HIGH <40.

**Actual folder names vs. the plan:** `Documentation/FolderStructure.md` specifies lower-case `android/`, `backend/`, `training/`, `dashboard/`, `data/`. The real repo uses `Android/`, `Backend/`, `ML/` (renamed from `training/`), `Dashboard/`, `Dataset/` (renamed from `data/`). Cosmetic, but worth knowing when cross-referencing the docs against the repo.

**Dataset decision (supersedes Architecture.md's original plan):** Training uses the public **UAH-DriveSet** (6 drivers, 6 vehicles, 500+ minutes, real phone sensors + 1 Hz GPS) instead of self-collected drives — documented and justified in `Documentation/Dataset Specification.md`. The raw dataset is present on disk at `Dataset/raw/UAH-DriveSet/` (**3.4 GB**, all 6 drivers D1–D6).

---

## 2. Completed components

| Layer | Owner | Status |
|---|---|---|
| 1–2 Android (Presentation + Comms) | Student A | **0% — not started** |
| 3 Backend API | Student B | Complete, tested (4/4 pytest) |
| 4 Processing ★ (the novelty layer) | Student B | Complete, tested |
| 5 ML model (training + runtime) | Student B | Complete, retrained with class balancing today |
| 6 Explainability (SHAP) | Student B | Complete — real SHAP wired both global and local (fixed today) |
| 7 Data (SQLite) | Student B | Complete |
| 8 Dashboard (Streamlit) | Student A | **0% — not started** |
| Documentation | Both | Complete (6 docs, internally consistent except where noted in §9) |

Everything Student B owns (Backend + ML + SHAP) is code-complete and passing its own tests. Everything Student A owns (Android + Dashboard) has not been started — both folders are empty directories with zero files, confirmed by direct filesystem inspection and `git status`.

---

## 3. Missing components

- **`Android/`** — entirely empty. No Room, no Retrofit, no UI, nothing.
- **`Dashboard/`** — entirely empty. No Streamlit app, no pages, no `db.py`.
- **`Backend/tests/test_processing.py`, `test_curve_density.py`** — planned in `FolderStructure.md`, never created. Only `test_api.py` exists. The project's headline novelty feature (`curve_density`) has no dedicated unit test.
- **`ML/src/ml_diagnostic.py`** — documented as delivered in `DELIVERY_SUMMARY.txt` ("Verifies all training outputs exist... Reports feature/window counts"), but does not exist anywhere in `ML/src/`.
- **`.gitignore`** — does not exist anywhere in the repo. Only `gitignore_additions.txt` (the intended *content* for one) sits unused at the project root. See §9, this is the highest-severity finding in this document.
- **Own-collected validation drives** — Architecture.md's original data-collection plan was deferred in favor of UAH-DriveSet; `Dataset Specification.md` §8 earmarks own-drive collection (deliberately curvy routes) for later validation, but none has happened yet.
- **`ML/notebooks/`** — planned in `FolderStructure.md` for exploration; absent. Explicitly non-essential ("never the source of truth"), so low priority.
- **`Papers/`** — empty. Presumably intended for the cited base paper / `ReportPhase1.pdf` / related literature; not part of the locked architecture.

---

## 4. Android implementation plan

Nothing exists yet, so this is a from-scratch plan, built directly from `Documentation/FolderStructure.md`'s locked package layout and `Documentation/API.md`'s frozen contract (both already written and stable — Android can be built with zero backend coordination).

**Package layout (from FolderStructure.md, MVVM):**
```
Android/app/src/main/java/com/driverisk/app/
├── data/
│   ├── local/          Room: TripEntity, SensorDataEntity, UploadStatusEntity + DAOs + DriveRiskDatabase
│   ├── remote/          Retrofit: DriveRiskApi (4 endpoints), RetrofitClient, dto/ (mirrors API.md field-for-field)
│   └── repository/      TripRepository, UploadRepository — ONLY classes touching Room/Retrofit
├── sensors/              SensorCollector (accel+gyro @50Hz), LocationCollector (GPS @1Hz), TripDetector
├── service/              TripRecordingService — foreground service, survives screen-off
├── ui/                   home/ recording/ history/ result/ map/ — Fragment + ViewModel pairs
└── util/                 Constants, RiskColorMapper (LOW=green, MEDIUM=amber, HIGH=red)
```

**Hard rules from the docs (violating these breaks the contract):**
- A Fragment must never see a DAO or Retrofit interface directly — only Repositories touch those.
- Room entities and Retrofit DTOs are separate classes. Never annotate one class for both.
- The app does **no** feature extraction and **no** prediction. It records, stores, uploads, displays. All intelligence is server-side.
- Sensor field names are locked: `accel_x/y/z`, `gyro_x/y/z` — no aliasing, no renaming.
- Uploads are batched at exactly 500 rows per call (`API.md`, `MAX_BATCH_SIZE` in `Backend/app/config.py`).

**Suggested build order (each step is independently testable against the already-working Backend):**
1. Room entities + DAOs mirroring `Database.md` §1–2 (`trips`, `raw_sensor_data` shape).
2. Retrofit DTOs mirroring `API.md` exactly, plus `DriveRiskApi` interface and `RetrofitClient`. Point it at a locally-running `uvicorn app.main:app` and confirm `POST /trips` round-trips.
3. Repositories (`TripRepository`, `UploadRepository`) wrapping Room + Retrofit.
4. `SensorCollector` + `LocationCollector` + `TripDetector` (manual Start/Stop, or auto-stop at speed≈0 for N seconds).
5. `TripRecordingService` as a foreground service so recording survives screen-off.
6. Batch upload with retry (500 rows/call) — **be aware**: the Backend does not currently deduplicate a resent `batch_index` despite `API.md` documenting that it does (see §9, finding #3). A naive "retry on any failure" loop could double-insert rows until that's fixed.
7. Result screen: `trip_score`, `risk_level`, `top_risk_factors` (from real SHAP now), event counts, Google Maps polyline colored by per-window `predicted_label`.
8. Trip History screen, then the dedicated Risk Map screen, then visual polish.

**Prerequisite not yet in place:** a Google Maps API key (needed for the Result screen's polyline and the dedicated Risk Map screen). Not found anywhere in the repo during this review — provision one before starting step 7.

**Why this is low-risk to start now:** the Backend's 4 endpoints are frozen, implemented, and pass an end-to-end test (`Backend/tests/test_api.py::test_full_round_trip`) using a synthetic trip. Android development can proceed against a running local Backend with no further backend changes required, except the batch-dedup fix noted above.

---

## 5. Backend status

**Code-complete** against `FolderStructure.md`'s plan — every file it specifies exists except the two missing test files noted in §3. Verified by reading every `.py` file in `Backend/app/`.

- **API (Layer 3)** — all 4 endpoints implemented in `app/api/routes/trips.py`: `POST /trips`, `POST /trips/{id}/upload`, `POST /trips/{id}/process`, `GET /trips/{id}/result`. Error envelope matches `API.md` exactly (`app/api/errors.py`). Route code orchestrates only — no inline SQL or math, as required.
- **Schemas (Layer 3)** — Pydantic models in `app/schemas/` mirror `API.md` field-for-field.
- **Models (Layer 7)** — SQLAlchemy models in `app/models/` mirror `Database.md`'s 5 tables exactly, including the locked `TripStatus` enum and the `(trip_id, window_index)` / `(trip_id, rank)` unique constraints.
- **Processing (Layer 4, ★ the novelty)** — `preprocessing.py`, `windowing.py`, `features.py`, `road_geometry.py`, `curve_density.py`, orchestrated in locked order by `pipeline.py`. All 24 features match `Database.md`'s column list exactly.
- **ML (Layer 5)** — `loader.py` loads the 4 artifacts once at startup; `predictor.py` does per-window inference; `aggregator.py` implements the locked `trip_score` formula and stores `weight_w1`/`weight_w2` per-trip for reproducibility. `model_wrapper.py`'s `LabelDecodingClassifier` normalizes RandomForest (string-native) vs. XGBoost (integer-encoded) so the rest of the backend never needs to know which algorithm won.
- **Explainability (Layer 6)** — `shap_explainer.py` now runs real `shap.TreeExplainer` (fixed today; previously silently stuck on a placeholder heuristic even after the model was trained). `reason_text.py` produces direction-aware plain-language sentences (also fixed today — previously ignored `direction` for templated features).
- **Data (Layer 7)** — `database.py` enables WAL mode and `PRAGMA foreign_keys=ON` exactly as `Database.md`'s operational notes require.
- **Tests** — `Backend/tests/test_api.py`, 4/4 passing: full round trip, unknown-trip 404, duplicate-trip 409, result-before-process 409.
- **Model artifacts present** in `Backend/ml_model/`: `best_model.pkl` (XGBoost, F1_macro=0.9002), `scaler.pkl`, `feature_list.json` (24 features), `model_comparison.json`. The backend serves real predictions, not the placeholder heuristic — confirmed via `verify_feature_parity.py`'s "Backend Model Loading Test" step.

**Known gaps (in code comments / config, not yet actioned):**
- Event thresholds (`HARSH_BRAKE_THRESHOLD_MS2`, `HARSH_CORNER_GYRO_THRESHOLD`, `OVERSPEED_KMH`, `CURVE_HEADING_CHANGE_DEG` in `config.py`) are placeholder values pending real-data tuning.
- `accel_x`/`accel_y` → longitudinal/lateral mapping (`features.py`) is an explicit `[INFERRED]` assumption, correct for UAH's calibrated car-referenced axes but unverified for an actual Android phone's mounting orientation.
- Duplicate `batch_index` is not deduplicated — see §9 finding #3 for why this is now classified as a contract bug, not just a gap.

---

## 6. ML status

**Pipeline code-complete and running against the real dataset** (not synthetic) — `ML/src/step01_load_raw.py` through `export_artifacts.py`, all present and functional.

- **Dataset**: real UAH-DriveSet, 3.4 GB, all 6 drivers (D1–D6) present at `Dataset/raw/UAH-DriveSet/`. Produces 12,555 labeled windows (`ML/outputs/dataset_features_labeled.csv`).
- **Class balance**: severe (1240.5× LOW:HIGH — 12,405 LOW / 140 MEDIUM / 10 HIGH). Fixed today: `RandomForestClassifier(class_weight="balanced")` and `compute_sample_weight("balanced", y)` for XGBoost (which has no `class_weight` param). Test F1_macro improved **0.58 → 0.90**; HIGH-risk detection improved **0/2 → 2/2** correct on the test set.
- **Model selection**: `step09_select_best.py` picked **XGBoost** (F1_macro = 0.9002, vs. RandomForest's 0.8908) — this is the currently-exported `best_model.pkl`.
- **Global SHAP importance**: top features are `accel_long_min`, `accel_mag_max`, `accel_mag_std`, `accel_lat_max`, `jerk_max`. **`curve_density` ranks 19th of 24** and `curve_density_x_speed_mean` 20th — the project's headline novelty feature has weak signal on this specific dataset (see §9, this is a dataset limitation, not a code defect — `Dataset Specification.md` itself flags UAH's "secondary road" as not being an extreme mountain-curve route).
- **Two SHAP scripts exist side by side**: `step10_global_shap.py` (original) still has an axis-averaging bug that produces 3 "importance values" instead of 24 for the multiclass case — this is the exact bug this project hit before today's fix. `step10_global_shap_fixed.py` is the corrected version and is what `run_diagnostics_windows.py` actually calls. See §9 finding #4 — `ML/README.md`'s documented run order still points at the broken one.
- **Diagnostics tooling**: `verify_feature_parity.py`, `analyze_class_distribution.py`, `generate_training_summary.py`, `run_diagnostics_windows.py` all present and passing — running `python run_diagnostics_windows.py` from `ML/` regenerates `ML_Training_Summary.md` and confirms feature parity, class distribution, and SHAP completeness in one command.
- **Tests**: `ML/tests/test_pipeline_smoke.py`, 3/3 passing, synthetic-fixture based (folder discovery, full adapter chain, curvy-route curve-density sanity check). Explicitly does not and cannot validate model quality — that now comes from the real dataset numbers above.

---

## 7. Dashboard status

**0% — entirely unbuilt.** `Dashboard/` contains zero files.

Planned structure (`FolderStructure.md`, not yet created):
```
Dashboard/
├── app.py                   Streamlit entry, sidebar navigation
├── pages/
│   ├── 1_Overview.py         trip list, score distribution
│   ├── 2_Trip_Detail.py      single trip, events, SHAP factors
│   ├── 3_Risk_Map.py         route colored by window label
│   ├── 4_Model_Comparison.py reads model_comparison.json
│   └── 5_Feature_Importance.py global SHAP chart
└── db.py                     read-only connection to Backend/driverisk.db
```

**Everything the dashboard needs to read already exists and is real (not placeholder) data:** `Backend/driverisk.db` (schema live, populated with whatever trips have been processed via pytest so far), `Backend/ml_model/model_comparison.json` (real RF-vs-XGBoost metrics), `ML/outputs/shap_global_importance.json` (real, 24 features ranked). This can be built independently of Android — it has no dependency on the app existing, only on the DB file and JSON artifacts, both already present.

**Hard constraint from Architecture.md D8:** the dashboard opens the SQLite file directly and must never call the API and must never write to `driverisk.db` — read-only, always.

---

## 8. Remaining tasks

Roughly in priority order (severity/urgency reasoning is in §9):

1. Create the real `.gitignore` from `gitignore_additions.txt`'s content (trivial, urgent — see §9 #1).
2. Commit the currently-uncommitted work (all of `ML/`, the trained model artifacts, today's Backend fixes) — only after the `.gitignore` fix, so the 3.4 GB dataset and venvs don't get swept in.
3. Build the Android app (§4) — the single largest remaining piece of work, and the only thing blocking an actual end-to-end phone-to-result demo.
4. Build the Streamlit dashboard (§7) — independently buildable in parallel with Android; all its data dependencies already exist.
5. Fix `crud/sensor.py`'s missing `batch_index` deduplication, or amend `API.md` to stop promising it (§9 #3) — resolve the mismatch one way or the other.
6. Retire or fix `ML/src/step10_global_shap.py`'s axis bug, and update `ML/README.md`'s run order to reference the working script (§9 #4).
7. Add the two missing Backend test files (`test_processing.py`, `test_curve_density.py`) — the novelty feature currently has no dedicated unit test.
8. Remove the duplicate, untracked root-level `"Dataset Specification.md"` (canonical copy lives in `Documentation/`).
9. Resolve the K-Means/owner-monitoring scope conflict flagged in `Architecture.md` §8 before the viva.
10. Tune the placeholder event thresholds (`config.py`) against real drive data once available.
11. Validate the `accel_x`/`accel_y` longitudinal/lateral assumption against real phone-mounted data once Android exists.
12. Provision a Google Maps API key (needed for Android's Result/Risk Map screens and useful context for the dashboard's risk map too).
13. Consider collecting a small set of own deliberately-curvy validation drives to strengthen the `curve_density` novelty signal for the viva (§9 #9).

---

## 9. Bugs and risks

Ordered by severity, not by where they live.

1. **[HIGH] No `.gitignore` exists — 4+ GB of data the project cannot afford to commit is currently unprotected.** Confirmed by direct inspection: only `gitignore_additions.txt` (inert content, never applied) exists; there is no `.gitignore` anywhere in the repo. `git status` confirms `Dataset/` (**3.4 GB**, including the UAH-DriveSet raw data whose license explicitly forbids redistribution — `Dataset Specification.md` §7), `ML/` (including `ML/venv/`, **649 MB**), and the trained model artifacts are all currently **untracked**. A single `git add -A` or `git add .` would stage all of it. The repo has exactly **one commit** in its entire history (`8e59183 "documentation"` on branch `master`). **Fix is trivial:** rename/apply `gitignore_additions.txt` → `.gitignore` before the next `git add`.
2. **[HIGH] Almost all real work is uncommitted.** Following directly from #1: the entire `ML/` pipeline, the trained model, and today's Backend fixes (`shap_explainer.py`, `reason_text.py`, `loader.py` all show as modified; `model_wrapper.py` — the class the whole model-loading architecture depends on — shows as **never committed at all**) exist only on local disk. One disk failure or accidental `git clean -fd` away from losing it all.
3. **[MEDIUM] The frozen API contract is violated by the implementation.** `Documentation/API.md` states as a locked guarantee: *"Duplicate batch_index values are ignored rather than double-inserted, so the app can safely retry after a dropped connection."* `Backend/app/crud/sensor.py`'s own docstring admits: *"KNOWN GAP: resent batches... are not deduplicated yet."* These directly contradict each other. Since `API.md` changes require "a stated reason and approval," this needs a deliberate decision — implement the dedup, or formally amend the doc — not silent drift. It also directly affects the Android upload-retry logic planned in §4.
4. **[MEDIUM] `ML/src/step10_global_shap.py` still has the exact bug that opened this project's most recent debugging session.** It averages SHAP output over the wrong axes when `shap` returns a native 3D `(samples, features, classes)` array (assumes the old list-of-per-class-arrays shape instead), producing 3 "importance values" instead of 24. The corrected version, `step10_global_shap_fixed.py`, exists and is what `run_diagnostics_windows.py` actually runs — but **`ML/README.md`'s documented "Run order" section still tells a reader to run the broken original.** Anyone following the README verbatim reproduces the bug.
5. **[LOW-MEDIUM] `ML/src/ml_diagnostic.py` is documented as delivered but does not exist.** `DELIVERY_SUMMARY.txt` lists it with a specific description of what it does; it is not present in `ML/src/`. Low severity since its function is now covered by `verify_feature_parity.py` + `generate_training_summary.py`, but the doc is misleading as written.
6. **[MODEL RISK] The HIGH-risk class has only 10 labeled windows in the entire 12,555-window dataset (0.08%).** Even after today's class-balancing fix (test F1_macro 0.58→0.90, HIGH now 2/2 correct), "2/2" is 2 examples. This is a real, structural dataset-scale limitation — more code cannot fix it, only more (or differently sourced) data can. Frame any HIGH-risk accuracy claims at the viva accordingly.
7. **[MODEL RISK] The project's headline novelty feature is weak on this dataset.** `curve_density` and `curve_density_x_speed_mean` rank 19th and 20th of 24 features by SHAP importance. `Dataset Specification.md` itself flags this honestly: UAH's "secondary road" is a normal regional road, not an intentionally curvy route. Likely to draw a direct question at the viva ("if curve density is your novelty, why is it barely used?") — worth having the dataset-limitation explanation ready, or collecting a small curvy-road validation set beforehand (§8 #13).
8. **[PROCESS RISK] Unresolved scope conflict, flagged but not decided.** `Architecture.md` §8: `ReportPhase1.pdf` (already submitted to the college) promises K-Means driver profiling and an owner-monitoring feature; neither is in the locked design scope. Needs an explicit decision — add a scoped K-Means panel to the dashboard, or add a documented scope-change note — before the viva, not during it.
9. **[LOW] Two copies of the dataset spec doc exist**, one canonical (`Documentation/Dataset Specification.md`, tracked... actually also untracked per `git status` — see below) and one stray duplicate at the project root (`"Dataset Specification.md"`, untracked). Low risk of drift since both are currently untracked, but should be cleaned up before the first real commit.
10. **[LOW] `Documentation/Dataset Specification.md` itself is untracked in git**, despite `Documentation/`'s other 5 files apparently being part of the single existing "documentation" commit. Worth confirming what actually landed in that commit before assuming the docs are safely versioned.
11. **[LOW] `accel_x`/`accel_y` axis assumption is unverified for real phones.** Correct by construction for UAH's calibrated, car-referenced axes; explicitly flagged `[INFERRED]` in `features.py` for the real Android case, where phone mounting orientation varies. No way to close this until real phone data exists.

---

## 10. Suggested implementation order

Sequenced for a single person continuing solo; if a second contributor is active, Android (Student A track) and anything ML/Backend (Student B track) can run fully in parallel from step 2 onward, per the original team split.

1. **Repo hygiene, today, before anything else (~15 min, zero risk):** apply `.gitignore` from `gitignore_additions.txt`; delete the stray duplicate `"Dataset Specification.md"`; then commit the current tree (ML pipeline, model artifacts, today's Backend fixes). Everything after this point should be committed incrementally — the project currently has a single commit covering multiple days of work, which is itself a risk.
2. **Close the two concrete Backend bugs (~1–2 hours):** fix (or formally waive) `batch_index` deduplication; retire or fix `step10_global_shap.py`'s axis bug and correct `ML/README.md`'s run order.
3. **Android MVP (the critical path — days, not hours):** work through §4's build order — Room + Retrofit scaffold first (independently testable against the already-passing Backend), then sensors/trip-detection, then batch upload, then the Result screen. This is the only remaining piece that blocks having an actual phone-to-result working demo; nothing else in this document blocks it or is blocked by it.
4. **Streamlit dashboard (parallelizable with step 3, or sequenced after — hours to ~1–2 days):** every data dependency it needs (`driverisk.db`, `model_comparison.json`, `shap_global_importance.json`) already exists and is real, not placeholder, so this has no dependency on Android being done first.
5. **Add the missing Backend tests** (`test_processing.py`, `test_curve_density.py`) — cheap, and closes the gap on the one feature (`curve_density`) most likely to be scrutinized at the viva.
6. **Integration pass:** once Android exists, run one real trip phone → Backend → Result screen end-to-end and confirm it matches what `test_full_round_trip` already proves works with synthetic data.
7. **Viva-readiness pass, last:** resolve the K-Means/owner-monitoring scope conflict (§9 #8); decide whether to collect a small curvy-road validation set to address the weak `curve_density` SHAP ranking (§9 #7); tune event thresholds if time remains; be ready to speak honestly to the HIGH-class sample-size limitation (§9 #6) rather than overclaim accuracy.
