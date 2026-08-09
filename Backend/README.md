# Backend

FastAPI backend implementing Layers 3–7 of `Documentation/Architecture.md`.

## Setup

```powershell
cd Backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

## Run

```powershell
uvicorn app.main:app --reload --port 8000
```

Swagger UI: http://127.0.0.1:8000/docs
Health check: http://127.0.0.1:8000/health — tells you whether a trained model is loaded or the placeholder heuristic is active.

## Test

```powershell
pytest tests/ -v
```

## Status

- `POST /trips`, `POST /trips/{id}/upload` — fully implemented.
- `POST /trips/{id}/process`, `GET /trips/{id}/result` — fully implemented and **verified working end-to-end**, but currently scored by a transparent **placeholder heuristic**, since `ML/` hasn't produced `best_model.pkl` yet. Preprocessing, windowing, feature extraction, road geometry and curve density are the **real** implementations — they don't depend on a trained model.
- Once `ML/export_artifacts.py` copies `best_model.pkl`, `scaler.pkl` and `feature_list.json` into `ml_model/`, the same endpoints automatically switch to the real model and real SHAP. No route code changes needed — check `/health` to confirm `model_loaded: true`.

## Known gaps (tracked, not blocking)

- Event thresholds in `app/config.py` (harsh brake/accel/corner, overspeed, curve angle) are placeholder values from `Architecture.md` — must be tuned against real drive data once `Dataset/` has sessions covering curvy roads.
- `accel_x`/`accel_y` are treated as longitudinal/lateral respectively — confirm this matches the actual phone mounting orientation used during data collection.
