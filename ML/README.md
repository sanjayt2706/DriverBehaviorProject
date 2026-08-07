# ML/

Pipeline A (offline training), now built against the **UAH-DriveSet** public
dataset instead of self-collected drives. See
`Documentation/Dataset Specification.md` for the full rationale, licensing,
and column mapping.

## Setup

```powershell
cd ML
python -m venv venv
venv\Scripts\activate
pip install pandas scikit-learn xgboost shap joblib matplotlib pytest
```

1. Download UAH-DriveSet (see `Dataset/README.md`) into
   `Dataset/raw/UAH-DriveSet/`.
2. Make sure `Backend/` has its own dependencies installed too (steps 04+
   import `Backend/app/processing` directly).

## Run order

```powershell
cd ML\src
python step04_build_features.py   # discover + adapt + window + feature + label
python step05_split_scale.py      # trip-grouped 80/20 split, fit scaler
python step06_train_rf.py         # train Random Forest
python step07_train_xgb.py        # train XGBoost
python step08_evaluate.py         # metrics + 5-fold CV -> model_comparison.json
python step09_select_best.py      # pick higher F1, wrap, export best_model.pkl
python step10_global_shap.py      # global SHAP importance for the dashboard
python export_artifacts.py        # final checkpoint - confirms all 4 files present
```

`step01_load_raw.py`, `step02_clean.py` and `step03_label.py` are called
internally by `step04_build_features.py` - they're not meant to be run
standalone in normal use, but each can be run alone (`python step01_load_raw.py`)
to sanity-check just that stage.

After `export_artifacts.py` confirms all four files are in `Backend/ml_model/`,
restart the Backend and check `GET /health` — `model_loaded` should now be
`true` and `model_name` should say `RandomForest` or `XGBoost`, not
`PLACEHOLDER_HEURISTIC`.

## Verify without the real dataset

```powershell
cd ML
pytest tests/ -v
```

This runs the UAH file-format adapter (axis remap, unit conversion,
upsampling, event-based labeling) against a small synthetic fixture
generated on the fly, so you can confirm the pipeline code itself is
correct before spending time downloading the ~500-minute real dataset.
It does **not** validate model quality — only that the code runs and
produces sane shapes.

## What's dataset-specific vs. shared

| File | Dataset-specific? |
|---|---|
| `step01_load_raw.py` | Yes — UAH folder discovery |
| `step02_clean.py` | Yes — UAH axis remap, unit conversion, gyro derivation, upsampling |
| `step03_label.py` | Yes — UAH `EVENTS_INERTIAL` severity → LOW/MEDIUM/HIGH |
| `step04_build_features.py` onward | No — calls `Backend/app/processing` and standard sklearn/xgboost, same code that will run against your own collected data later |

This split is deliberate (Architecture.md's shared-code rule): only steps
01–03 need to change when you add your own collected trips. See
`Documentation/Dataset Specification.md` → "Replacing or augmenting with
your own data" for exactly how.
