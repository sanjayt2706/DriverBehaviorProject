"""
ML/src/step09_select_best.py
Pipeline A, step 9: pick the model with the higher test F1-Score.
"THIS IS THE ONLY PLACE COMPARISON HAPPENS" (Architecture.md Section 6) -
at runtime, the backend loads and runs exactly one model.

The winning model is wrapped in app.ml.model_wrapper.LabelDecodingClassifier
so it always exposes predict() -> LOW/MEDIUM/HIGH strings, regardless of
whether RandomForest (string-native) or XGBoost (integer-encoded
internally) won - see Backend/app/ml/model_wrapper.py for why this exists.
"""
import json
import sys
from pathlib import Path

import joblib

ML_ROOT = Path(__file__).resolve().parent.parent
PROJECT_ROOT = ML_ROOT.parent
sys.path.insert(0, str(PROJECT_ROOT / "Backend"))
from app.config import ML_MODEL_DIR, MODEL_PATH  # noqa: E402
from app.ml.model_wrapper import LabelDecodingClassifier  # noqa: E402

sys.path.insert(0, str(ML_ROOT / "src"))
from step06_train_rf import MODEL_PATH as RF_PATH  # noqa: E402
from step07_train_xgb import MODEL_PATH as XGB_PATH, LABEL_ENCODER_PATH  # noqa: E402
from step08_evaluate import OUTPUT_JSON as COMPARISON_JSON  # noqa: E402


def main():
    comparison = json.loads(COMPARISON_JSON.read_text())
    rf_f1 = comparison["RandomForest"]["test"]["f1_macro"]
    xgb_f1 = comparison["XGBoost"]["test"]["f1_macro"]

    if rf_f1 >= xgb_f1:
        winner = "RandomForest"
        model = joblib.load(RF_PATH)
        wrapped = LabelDecodingClassifier(model, label_encoder=None, algorithm_name="RandomForest")
    else:
        winner = "XGBoost"
        model = joblib.load(XGB_PATH)
        encoder = joblib.load(LABEL_ENCODER_PATH)
        wrapped = LabelDecodingClassifier(model, label_encoder=encoder, algorithm_name="XGBoost")

    ML_MODEL_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(wrapped, MODEL_PATH)

    comparison["selected_model"] = winner
    comparison["selected_f1_macro"] = max(rf_f1, xgb_f1)
    COMPARISON_JSON.write_text(json.dumps(comparison, indent=2))
    # Also copy into ml_model/ so the dashboard's Model Comparison page can
    # read it without reaching into ML/outputs/.
    (ML_MODEL_DIR / "model_comparison.json").write_text(json.dumps(comparison, indent=2))

    print(f"Selected {winner} (F1_macro={max(rf_f1, xgb_f1):.4f}). Saved to {MODEL_PATH}")


if __name__ == "__main__":
    main()
