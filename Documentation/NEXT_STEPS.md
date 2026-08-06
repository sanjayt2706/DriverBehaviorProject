# NEXT STEPS — Backend Skeleton Complete

**Status:** Backend skeleton (Layers 3–7) is done, tested, and verified end-to-end with a placeholder predictor. All four API endpoints are frozen and working.

---

## Immediate actions (before split work)

### 1. Integrate Backend into your repo

```powershell
cd D:\MajorProject\DriverBehaviorProject
Expand-Archive Backend.zip -DestinationPath . -Force  # overwrites the empty Backend/ folder

cd Backend
git add .
git commit -m "Backend skeleton: models, schemas, routes, processing, placeholder ML"
git push
```

### 2. Put the four spec docs in Documentation/

```powershell
cp docs/Architecture.md Documentation/
cp docs/API.md Documentation/
cp docs/Database.md Documentation/
cp docs/FolderStructure.md Documentation/

git add Documentation/
git commit -m "Add frozen architecture specs"
```

---

## Now: split work between the two students (Days 2–4)

You have a **frozen contract** (API.md). You have real preprocessing/features/curve density working. You can build Android and ML **in parallel** against this contract with zero coordination risk after this point.

### Student A — Android (Layers 1–2)

**Goal for Day 4 MVP:** App records a trip locally in Room, uploads it as 500-row batches to the Backend via Retrofit, displays the result on the Result screen.

Start with:
- Room entities mirroring `Database.md` sections 1–2 (trip, sensor_data, upload_status)
- Retrofit DTOs mirroring `API.md` (CreateTripRequest, UploadBatchRequest, etc.)
- Sensor collection (accelerometer 50 Hz, gyroscope 50 Hz, GPS 1 Hz)
- Trip detector (start/stop buttons, or auto-stop when speed ≈ 0 for N seconds)
- Batch upload with retry logic (500 rows per call)
- Result screen showing trip_score, risk_level, top_risk_factors, Google Maps coloured by window risk

**No feature extraction, no predictions, no ML code.** The app is dumb; all smarts live on the Backend.

Use `API.md` as your Retrofit interface spec — field names, request/response shapes, error codes are all in there.

### Student B — ML Training Pipeline (Pipeline A, offline)

**Goal for Day 4 MVP:** At least 2–3 real driving sessions collected (city + highway + curvy road is the ideal mix).

Days 2–3: Data collection drives (this is the long pole). You need:
- 8–12 sessions total, 4–6 hours total driving
- 2 drivers (you two), 1–2 vehicles
- Must include curvy roads (without them, curve density has no signal and the novelty claim fails)
- Label each drive SAFE / MODERATE / RISKY + thresholds or manual review

Day 4: Start the training pipeline:
- Load raw CSVs
- Clean, preprocess, sliding window
- **Import `app.processing` from Backend** — do not reimplement features
- Compute features + road geometry + curve density
- Split 80/20, train RF + XGBoost
- Compare, select the higher F1 model
- Export `best_model.pkl`, `scaler.pkl`, `feature_list.json`, `model_comparison.json` to `Backend/ml_model/`

Once those four files are in place, Backend automatically switches from placeholder to real predictions. Hit `/health` to confirm `model_loaded: true`.

**Training pipeline lives in `ML/src/step01_load_raw.py` → `step10_global_shap.py` → `export_artifacts.py`** (see `FolderStructure.md`).

---

## Commit strategy

Commit early and often. One sensible breakpoint per student:

**Student A:**
```
"Android: Room entities + data models"
"Android: Retrofit client + API DTOs"
"Android: Sensor collection + trip detection"
"Android: Batch upload with retry"
"Android: Result screen with maps"
```

**Student B:**
```
"ML: data collection drive log + raw CSVs"
"ML: training pipeline steps 1–7 (features)"
"ML: training pipeline steps 8–10 (train, select, export)"
```

---

## Git workflow for the two of you

Since you're editing different top-level folders, merge conflicts are unlikely:

1. Both pull `master` to get the frozen specs and Backend skeleton.
2. A works in `Android/` and `Dashboard/`.
3. B works in `ML/` and stays hands-off Android.
4. Every commit gets pushed to the shared `master`.
5. If both need to touch `Backend/` later (rare), communicate first.

---

## The remaining architecture work (after MVP)

Days 5–15 are refinement + the full pipeline. Watch for these:

- **Streamlit dashboard** (Student A) — reads `driverisk.db` directly, shows model comparison, global SHAP importance, risk map, trip history. Template in `FolderStructure.md` `dashboard/pages/`.
- **Real SHAP wiring** (Student B) — right now `app/explain/shap_explainer.py` falls back to a heuristic. Once the model is trained, wire up `shap.TreeExplainer(model).shap_values(...)`. The route code doesn't change; it's a drop-in replacement.
- **Event thresholds** (Student B) — the harsh-brake/accel/corner/overspeed thresholds in `config.py` are placeholders. Tune them against real drive data. Make them configurable so you can A/B test.
- **Google Maps risk map** (Student A) — colour the trip route by window risk (LOW green, MEDIUM amber, HIGH red). Polyline with dynamic colouring.

---

## How to verify everything works when you reunite

**After Student B exports the trained model:**

1. Backend auto-detects `best_model.pkl` and switches from placeholder to real predictions.
2. Student A's Android app should work unchanged — the contract hasn't changed.
3. Student B's Streamlit dashboard queries `driverisk.db` and renders real results.
4. Run `Backend/tests/ pytest` to spot any surprises.

---

## Summary: what each student owns

| Phase | Student A | Student B |
|---|---|---|
| **Days 1–2** | Room + Retrofit scaffold | Set up ML pipeline structure, plan drives |
| **Days 2–4 (MVP)** | Sensor collection, batch upload, Result screen | Collect 3+ real drives, run training pipeline |
| **Days 5–15** | Streamlit dashboard, Google Maps risk map, result screen polish | SHAP wiring, event threshold tuning, global feature importance, retraining loop |

Everything in `Documentation/` is the **law**. When in doubt, that's the spec.

Good luck. Message me when either of you hits an architecture ambiguity — I'm here to unblock, not to let ambiguity become technical debt.
