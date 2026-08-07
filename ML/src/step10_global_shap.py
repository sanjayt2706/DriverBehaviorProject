"""
ML/src/step10_global_shap.py
Pipeline A, step 10: global SHAP feature importance across the test set,
for the Streamlit dashboard's Feature Importance page (Layer 8).

Runs on the RAW winning model (not the LabelDecodingClassifier wrapper),
since shap.TreeExplainer needs direct access to the underlying tree
ensemble. Local (per-trip) SHAP explanation at runtime is a separate,
still-placeholder concern - see Backend/app/explain/shap_explainer.py.
"""
import json
import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import shap
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ML_ROOT = Path(__file__).resolve().parent.parent
PROJECT_ROOT = ML_ROOT.parent
sys.path.insert(0, str(PROJECT_ROOT / "Backend"))
from app.config import ML_MODEL_DIR  # noqa: E402

sys.path.insert(0, str(ML_ROOT / "src"))
from step04_build_features import FEATURE_COLUMNS  # noqa: E402
from step05_split_scale import TEST_CSV  # noqa: E402
from step06_train_rf import MODEL_PATH as RF_PATH  # noqa: E402
from step07_train_xgb import MODEL_PATH as XGB_PATH  # noqa: E402
from step09_select_best import COMPARISON_JSON  # noqa: E402

OUTPUT_JSON = ML_ROOT / "outputs" / "shap_global_importance.json"
OUTPUT_PNG = ML_ROOT / "outputs" / "shap_global_importance.png"


def main():
    comparison = json.loads(COMPARISON_JSON.read_text())
    winner = comparison["selected_model"]
    raw_model = joblib.load(RF_PATH if winner == "RandomForest" else XGB_PATH)

    test_df = pd.read_csv(TEST_CSV)
    scaler = joblib.load(ML_MODEL_DIR / "scaler.pkl")
    X_test = scaler.transform(test_df[FEATURE_COLUMNS])

    explainer = shap.TreeExplainer(raw_model)
    shap_values = explainer.shap_values(X_test)

    # Multi-class output: list of arrays (one per class) for some models,
    # a single 3D array for others depending on shap/model version.
    if isinstance(shap_values, list):
        mean_abs = np.mean([np.abs(sv) for sv in shap_values], axis=(0, 1))
    else:
        mean_abs = np.mean(np.abs(shap_values), axis=tuple(range(shap_values.ndim - 1)))

    importance = sorted(
        zip(FEATURE_COLUMNS, mean_abs.tolist()), key=lambda kv: kv[1], reverse=True
    )

    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_JSON.write_text(json.dumps(
        {"model": winner, "importance": [{"feature": f, "mean_abs_shap": v} for f, v in importance]},
        indent=2,
    ))

    names, values = zip(*importance)
    plt.figure(figsize=(8, max(4, len(names) * 0.3)))
    plt.barh(names[::-1], values[::-1])
    plt.xlabel("mean |SHAP value|")
    plt.title(f"Global feature importance ({winner})")
    plt.tight_layout()
    plt.savefig(OUTPUT_PNG, dpi=120)

    print(f"Wrote {OUTPUT_JSON} and {OUTPUT_PNG}")
    print("Top 5 features:", [n for n, _ in importance[:5]])


if __name__ == "__main__":
    main()
