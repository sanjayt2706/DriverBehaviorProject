# ML/

Pipeline A (offline training), built against the **UAH-DriveSet** public
dataset instead of self-collected drives.

See `Documentation/Dataset Specification.md` for:

- Dataset selection rationale
- Licensing requirements
- Column mapping
- Adapter implementation
- Replacing UAH with your own collected data later

---

# Setup

```powershell
cd ML
python -m venv venv
venv\Scripts\activate

pip install pandas scikit-learn xgboost shap joblib matplotlib pytest sqlalchemy pydantic fastapi uvicorn
```

## Dataset

1. Download **UAH-DriveSet** (see `Dataset/README.md`).
2. Extract it into:

```text
Dataset/raw/UAH-DriveSet/
```

3. Ensure the Backend dependencies are also installed because
steps 04 onward reuse:

```text
Backend/app/processing/
```

instead of duplicating preprocessing code.

---

# Training Pipeline

Run the scripts **in this exact order**.

```powershell
cd ML\src

python step04_build_features.py
python step05_split_scale.py
python step06_train_rf.py
python step07_train_xgb.py
python step08_evaluate.py
python step09_select_best.py
python step10_global_shap_fixed.py
python export_artifacts.py
```

---

## What each step does

### step04_build_features.py

- Discovers UAH trips
- Loads raw files
- Cleans data
- Windowing (5 s)
- Feature extraction
- Road geometry
- Curve density
- Creates labeled feature dataset

---

### step05_split_scale.py

- Train/Test split (trip grouped)
- 80/20 split
- Fits StandardScaler

---

### step06_train_rf.py

Trains Random Forest.

---

### step07_train_xgb.py

Trains XGBoost.

---

### step08_evaluate.py

Generates:

- Accuracy
- Precision
- Recall
- Macro F1
- Cross Validation
- Confusion Matrix
- model_comparison.json

---

### step09_select_best.py

Chooses the model with the best Macro F1 score.

Exports:

```text
Backend/ml_model/best_model.pkl
```

---

### step10_global_shap_fixed.py

Generates:

- Global SHAP feature importance
- shap_global_importance.json
- SHAP plots

(**Use this script instead of the older `step10_global_shap.py`**.)

---

### export_artifacts.py

Verifies all required deployment artifacts exist and copies them to:

```text
Backend/ml_model/
```

---

# Internal Steps

These are automatically called by `step04_build_features.py`.

Normally you **do not** run them manually.

```
step01_load_raw.py
step02_clean.py
step03_label.py
```

They can still be executed individually for debugging.

Example:

```powershell
python step01_load_raw.py
```

---

# Expected Output

After running the complete pipeline, the Backend should contain:

```text
Backend/
└── ml_model/
    ├── best_model.pkl
    ├── scaler.pkl
    ├── feature_list.json
    ├── shap_global_importance.json
    └── ...
```

---

# Backend Verification

Restart the Backend.

Open:

```
GET /health
```

Expected:

```json
{
  "model_loaded": true,
  "model_name": "RandomForest"
}
```

or

```json
{
  "model_loaded": true,
  "model_name": "XGBoost"
}
```

It should **NOT** say:

```
PLACEHOLDER_HEURISTIC
```

---

# Verify Without the Real Dataset

```powershell
cd ML

pytest tests/ -v
```

This executes the pipeline using a synthetic UAH-format fixture.

It validates:

- Axis remapping
- Unit conversion
- Gyroscope derivation
- Upsampling
- Event labeling
- Feature extraction

It **does not** measure model quality.

---

# Dataset-specific vs Shared Code

| File | Dataset Specific? |
|------|-------------------|
| step01_load_raw.py | Yes |
| step02_clean.py | Yes |
| step03_label.py | Yes |
| step04_build_features.py onward | No |

The design intentionally shares:

```
Backend/app/processing/
```

between:

- Offline ML training
- Runtime Backend predictions

to guarantee identical feature extraction.

---

# Replacing UAH with Your Own Data

Only these files change:

```
step01_load_raw.py
step02_clean.py
step03_label.py
```

Everything from:

```
step04_build_features.py
```

onward remains exactly the same.

See:

```
Documentation/Dataset Specification.md
```

for the complete migration procedure.

---

# Troubleshooting

## ModuleNotFoundError

Install missing packages:

```powershell
pip install sqlalchemy pydantic fastapi uvicorn matplotlib shap
```

---

## model_loaded = false

Check:

```
Backend/ml_model/
```

contains:

- best_model.pkl
- feature_list.json
- scaler.pkl

---

## SHAP errors

Always run:

```powershell
python step10_global_shap_fixed.py
```

Do **not** use:

```powershell
python step10_global_shap.py
```

because it is retained only for reference and is not compatible with the current SHAP implementation.

---

# Notes

The training pipeline and runtime backend intentionally share the same preprocessing and feature extraction code to guarantee feature parity.

No feature engineering logic is duplicated between ML training and production inference.