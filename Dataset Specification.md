# Dataset Specification.md

**Decision:** Initial model training uses the **UAH-DriveSet** public dataset instead of self-collected drives. Own-collected trips (Architecture.md's original plan) are deferred to validation and demonstration only, per your instruction. This document is the authoritative reference for that dataset — its structure, the mapping onto this project's locked schema, and exactly what preprocessing happens before training.

---

## 1. Dataset source

**UAH-DriveSet** — Romera, E., Bergasa, L.M., and Arroyo, R. (2016). *"Need Data for Driver Behaviour Analysis? Presenting the Public UAH-DriveSet."* IEEE 19th International Conference on Intelligent Transportation Systems (ITSC), pp. 387–392, Rio de Janeiro, Brazil.

- **Download:** http://www.robesafe.uah.es/personal/eduardo.romera/uah-driveset/
- **Cost:** Free. Click-through license agreement + email address, no payment, no formal application review, no waiting period.
- **Collected by:** University of Alcalá (UAH), Spain, using their own smartphone app **DriveSafe**.
- **Scale:** 6 drivers, 6 different vehicles (including one fully electric), 3 simulated behaviors (normal, drowsy, aggressive), 2 road types (motorway, secondary), **500+ minutes** of naturalistic driving (comparable to this project's original 4–6 hour own-collection target — Architecture.md Section 6).
- **Sensors:** Real smartphone accelerometer + gyroscope-equivalent (orientation) + GPS, captured by an actual windshield-mounted phone during real road driving — not a simulator, not synthetic.

---

## 2. Why this dataset over the alternatives

Three public options were considered. GPS availability was the deciding factor, since this project's headline novelty — **curve density** — is computed entirely from the GPS path (Architecture.md D1). A dataset without GPS cannot support the feature this project is built around.

| Dataset | Accel/Gyro | GPS | License | Verdict |
|---|---|---|---|---|
| **UAH-DriveSet** | Yes (real phone) | **Yes, 1 Hz** | Free, click-through | **Selected** |
| Kaggle "Driving Behavior Dataset" (the one cited in `ReportPhase1.pdf`'s own literature review) | Yes | **No** | Free | Rejected — no GPS means no road geometry, no curve density. Would gut the project's core contribution. Also only ~3,084 rows total, an order of magnitude smaller. |
| SHRP2 (the naturalistic driving study underlying `Robust_DataDriven_Framework...pdf`, the uploaded base paper) | Yes | Yes | Restricted — requires a formal data-use agreement with VTTI, often a multi-week approval process, and is sized in terabytes | Rejected — not "free" in the lightweight sense required here, and far beyond the scope of a 15-day project regardless of access |

Beyond just having GPS, UAH-DriveSet has three properties that matter specifically for this project:

1. **Two road types, including a genuinely curvier secondary road** (~90 km/h, mostly one lane each direction) alongside a straight motorway. This is exactly the road-type contrast Architecture.md's own dataset plan called for — without it, curve density has no variance to learn from.
2. **Per-event ground truth**, not just a per-trip label. The `EVENTS_INERTIAL` file gives a timestamp and a severity level (1/2/3) for every individual braking, turning, and acceleration event DriveSafe detected. This lets us assign labels *per 5-second window* instead of stamping an entire 15-minute trip with one label — a meaningfully better training signal, and directly compatible with this project's window-based architecture (Section 5 below).
3. **Comparable scale to the original plan.** 500+ minutes across 6 real drivers and 6 real vehicles is on the same order as — arguably better than — what two students could have collected in the 15-day window, and it's already labeled.

**Known limitation, carried forward honestly:** the "secondary road" is a normal Spanish regional road, not a mountain hairpin route. Curve density will have real signal but not extreme signal. Section 5 of `NEXT_STEPS.md` already earmarked own-drive collection for validation — deliberately curvy routes there would meaningfully strengthen this feature later (see Section 8 below).

---

## 3. Raw file structure

UAH-DriveSet is organized as one folder per driver, containing one subfolder per route/behavior combination:

```
Dataset/raw/UAH-DriveSet/
├── D1/
│   ├── <date>-<distance>km-D1-NORMAL-MOTORWAY/
│   │   ├── RAW_GPS.txt
│   │   ├── RAW_ACCELEROMETERS.txt
│   │   ├── EVENTS_INERTIAL.txt
│   │   ├── SEMANTIC_FINAL.txt
│   │   └── ... (other files not used by this pipeline)
│   ├── <date>-<distance>km-D1-AGGRESSIVE-MOTORWAY/
│   └── ...
├── D2/
└── ... D3, D4, D5, D6
```

Only three files per route are used by this project's pipeline:

### `RAW_GPS.txt` — 1 Hz

| Col | Field | Unit |
|---|---|---|
| 1 | timestamp | seconds since route start |
| 2 | speed | km/h |
| 3 | latitude | degrees |
| 4 | longitude | degrees |
| 5–9 | altitude, accuracy, course, etc. | (not used) |

### `RAW_ACCELEROMETERS.txt` — 10 Hz

| Col | Field | Unit |
|---|---|---|
| 1 | timestamp | seconds since route start |
| 2 | system-active flag | boolean (1 if speed > 50 km/h) |
| 3–5 | acceleration X, Y, Z | **G** |
| 6–8 | Kalman-filtered X, Y, Z | G (not used — see Section 4) |
| 9–11 | roll, pitch, yaw | degrees |

Axes are car-referenced after DriveSafe's calibration step: **Y = lateral** (reflects turning), **Z = longitudinal** (positive = accelerating, negative = braking). X is the remaining (roughly vertical) axis.

### `EVENTS_INERTIAL.txt` — event-driven, not periodic

| Col | Field |
|---|---|
| 1 | timestamp (s) |
| 2 | type (1=braking, 2=turning, 3=acceleration) |
| 3 | severity level (1=low, 2=medium, 3=high) |
| 4–5 | GPS lat/lon of the event |
| 6 | date |

Route folder names also encode the trip's overall behavior label (`NORMAL` / `DROWSY` / `AGGRESSIVE`) and road type (`MOTORWAY` / `SECONDARY`) — used as metadata and as a fallback label source (Section 6).

---

## 4. Preprocessing required before training

This is the substantive engineering work of adopting this dataset, implemented in `ML/src/step02_clean.py`. Four transforms are required to make UAH-DriveSet's raw files match this project's **locked** sensor schema (`accel_x/y/z`, `gyro_x/y/z` in m/s² and rad/s, per Architecture.md Section 1) — every one of them is necessary, none are optional:

| # | Problem | Fix |
|---|---|---|
| 1 | **Units.** UAH logs acceleration in G, this project uses m/s². | Multiply by 9.80665. |
| 2 | **Axis order.** UAH's calibrated axes are Y=lateral, Z=longitudinal, X=vertical. This project's `features.py` already assumes `accel_x`=longitudinal, `accel_y`=lateral (documented, flagged assumption). | Remap: UAH Z → `accel_x`, UAH Y → `accel_y`, UAH X → `accel_z`. |
| 3 | **No raw gyroscope.** UAH logs orientation (roll/pitch/yaw, degrees) instead of angular velocity. | Numerically differentiate orientation over time, convert deg/s → rad/s. This is a **documented proxy** for true angular-rate sensor output, not a real gyroscope reading — noted explicitly wherever it matters. |
| 4 | **Sample rate mismatch.** UAH's accelerometer is 10 Hz; this project's windowing assumes ~50 Hz (`Backend/app/config.py MIN_SAMPLES_PER_WINDOW`). At raw 10 Hz, 5-second windows would fall under the minimum sample threshold and get silently dropped. | Linear interpolation upsamples to 50 Hz before windowing. GPS (already 1 Hz in both UAH and production) needs no rate change. |

After these four transforms, the adapted samples are indistinguishable in shape from what the Android app would upload in production — they are fed into `Backend/app/processing/preprocessing.py`, `windowing.py`, `features.py`, `road_geometry.py`, and `curve_density.py` **unchanged**, exactly as Architecture.md's shared-code rule requires. Nothing in `Backend/` was modified to accommodate this dataset.

**One additional fix surfaced during implementation, not dataset-specific:** XGBoost's sklearn API requires integer-encoded class labels internally and returns integers from `.predict()`, while this project's locked runtime contract requires `LOW`/`MEDIUM`/`HIGH` strings. Rather than teach `Backend/app/ml/predictor.py` which algorithm won the comparison, a thin wrapper (`Backend/app/ml/model_wrapper.py::LabelDecodingClassifier`) is applied to whichever model wins at export time, so the runtime backend never needs to know or care which algorithm is inside `best_model.pkl`.

---

## 5. Label derivation (window-level LOW / MEDIUM / HIGH)

UAH-DriveSet's native labels are per-trip (`NORMAL`/`DROWSY`/`AGGRESSIVE`), but this project's model predicts per-**window** risk (Architecture.md Section 1). Stamping every window of a 15-minute trip with one trip-wide label would be a weak, noisy signal.

Instead, `ML/src/step03_label.py` uses `EVENTS_INERTIAL`'s real per-event severity as ground truth:

```
For each 5-second window:
    look at every inertial event whose timestamp falls inside it
    if the highest severity level present is 3  -> HIGH
    if the highest severity level present is 2  -> MEDIUM
    if the highest severity level present is 1  -> LOW
    if no event falls inside the window          -> LOW
```

This is evidence-based per window, not inherited from the whole trip's mood — a "normal" trip's one hard brake still produces a correctly-labeled HIGH window, and an "aggressive" trip's calm stretches are correctly labeled LOW. **Fallback:** if a route has no `EVENTS_INERTIAL` file at all (no per-event ground truth exists for it), every window in that route uses the trip-level behavior label instead (`NORMAL→LOW`, `DROWSY→MEDIUM`, `AGGRESSIVE→HIGH`) — a coarser substitute used only when nothing better is available.

This logic was verified against a synthetic fixture built to the documented file format (`ML/tests/test_pipeline_smoke.py`): a synthetic aggressive trip with injected severity-3 events correctly produced HIGH-labeled windows at those exact timestamps, and LOW elsewhere.

---

## 6. Train / validation / test split

**Locked split ratio (Architecture.md Section 6): 80% train / 20% test, plus 5-fold cross-validation on the train split for validation** — unchanged by the dataset swap. What changed is *how* the split is drawn:

**Split is grouped by `trip_id`, not by individual window.** Windows within one trip overlap 50% with their neighbors (Architecture.md's locked windowing scheme), so a naive random window split would put near-duplicate windows on both sides of the train/test boundary and inflate test accuracy. `GroupShuffleSplit` and `GroupKFold` (both from scikit-learn) guarantee every window from a given trip lands entirely in train or entirely in test/each fold. This is a correctness fix to how the already-locked 80/20 ratio is drawn, not a change to the ratio itself.

Implemented in `ML/src/step05_split_scale.py` (train/test) and `ML/src/step08_evaluate.py` (5-fold CV on train).

---

## 7. Licensing and citation

**License:** Free for academic and non-academic non-commercial use — research, teaching, publications, personal experimentation. Verbatim from the license agreement:

> *"This dataset is made freely available to academic and non-academic entities for non-commercial purposes such as academic research, teaching, scientific publications, or personal experimentation."*

**Restrictions that affect this repository:**

- **Do not commit `Dataset/raw/UAH-DriveSet/` to git.** The license explicitly prohibits redistribution: *"you do not distribute this dataset or modified versions."* Trained model artifacts (`best_model.pkl` etc.) are fine to commit and share — they're abstract representations, not the dataset itself — but the raw files are not. `Dataset/raw/` must be in `.gitignore`.
- **Each team member downloads it individually**, accepting the license with their own email. It cannot be shared as a zip between the two of you.
- **Non-commercial only.** Fine for a college project; would need a separate arrangement for any commercial use later.

**Required citation** (in the project report and anywhere the dataset is referenced):

> E. Romera, L. M. Bergasa and R. Arroyo, "Need Data for Driver Behaviour Analysis? Presenting the Public UAH-DriveSet," *IEEE 19th International Conference on Intelligent Transportation Systems (ITSC)*, pp. 387–392, Rio de Janeiro, Brazil, November 2016.

---

## 8. Replacing or augmenting with your own collected data — without changing the architecture

This was designed in from the start, not bolted on: **only `ML/src/step01_load_raw.py`, `step02_clean.py`, and `step03_label.py` are UAH-specific.** Everything from `step04_build_features.py` onward calls `Backend/app/processing` and standard scikit-learn/XGBoost — the exact same code path your own data will use.

To add your own drives later:

1. **Collect trips through the actual Android app**, uploaded through the real `POST /trips` / `POST /trips/{id}/upload` API into `driverisk.db`, exactly as originally planned (Architecture.md Section 6 dataset plan). No adapter needed — your own trips are already in the project's native schema, unlike UAH-DriveSet.
2. **Write one small script** (`ML/src/step01b_load_own_trips.py`, following the same pattern as `step01_load_raw.py`) that reads trips directly from `driverisk.db`'s `raw_sensor_data` table instead of parsing UAH's file format. It hands off to the exact same `clean_and_forward_fill` → `make_windows` → `extract_window_features` → `extract_road_geometry` → `extract_curve_density` chain — no changes to any of those files.
3. **Label your own trips** with a simplified version of `step03_label.py`'s logic: since you'll define your own harsh-event thresholds (already scaffolded in `Backend/app/config.py`, marked `[INFERRED]` pending real data), you can derive window labels directly from those thresholds rather than needing an `EVENTS_INERTIAL`-equivalent file.
4. **Concatenate.** `step04_build_features.py`'s output CSV has a `trip_id` and `driver` column already — own-collected trips are just additional rows with a different `trip_id` prefix. The trip-grouped split in step05 handles mixed-source datasets with no changes.
5. **Retrain.** Steps 05–10 run unchanged regardless of where the labeled feature rows came from.

Nothing in `Backend/`, the API contract, or the database schema needs to change at any point in this process — the entire point of Architecture.md's shared-code rule.

---

## 9. Verification performed

Since the real dataset requires an individual license acceptance this assistant cannot complete on your behalf, the adapter pipeline (steps 01–04) was verified against a synthetic fixture built to UAH-DriveSet's exact documented file format (`ML/tests/test_pipeline_smoke.py`, 3 passing tests):

- Folder discovery correctly parses driver/behavior/road from route folder names.
- The full adapter chain (axis remap → unit conversion → gyro derivation → upsampling → shared preprocessing/windowing/features/road-geometry/curve-density) runs without error and produces the correct schema.
- Event-based labeling correctly assigns HIGH to windows containing an injected severity-3 event, and LOW elsewhere.
- A synthetic curvy route produces nonzero curve density; a straight route does not.

The complete pipeline (steps 01 through `export_artifacts.py`, plus RandomForest, XGBoost, model selection, and global SHAP) was also run end-to-end against this synthetic data, confirming: the trained model exports correctly to `Backend/ml_model/`, the Backend automatically detects and loads it (`GET /health` → `model_loaded: true`, `model_name: "RandomForest"`), and a full trip through all four API endpoints returns real model predictions in place of the placeholder heuristic — no Backend code changes required.

**This verification proves the pipeline is correct. It does not — and cannot — validate model quality, since 3 synthetic trips carry no real statistical signal.** Real accuracy, F1, and confusion matrix numbers will only be meaningful once run against the actual downloaded UAH-DriveSet.
