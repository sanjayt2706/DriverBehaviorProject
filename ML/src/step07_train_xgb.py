"""
ML/src/step07_train_xgb.py
Pipeline A, step 7: train XGBoost with the locked hyperparameters
(Architecture.md Section 6): n_estimators=200, max_depth=6, learning_rate=0.1.
"""
import sys
from pathlib import Path

import joblib
import pandas as pd
from sklearn.preprocessing import LabelEncoder
from sklearn.utils.class_weight import compute_sample_weight
from xgboost import XGBClassifier

ML_ROOT = Path(__file__).resolve().parent.parent
PROJECT_ROOT = ML_ROOT.parent
sys.path.insert(0, str(PROJECT_ROOT / "Backend"))
from app.config import ML_MODEL_DIR  # noqa: E402

sys.path.insert(0, str(ML_ROOT / "src"))
from step04_build_features import FEATURE_COLUMNS  # noqa: E402
from step05_split_scale import TRAIN_CSV  # noqa: E402

MODEL_PATH = ML_ROOT / "outputs" / "xgb_model.pkl"
LABEL_ENCODER_PATH = ML_ROOT / "outputs" / "label_encoder.pkl"


def main():
    train_df = pd.read_csv(TRAIN_CSV)
    scaler = joblib.load(ML_MODEL_DIR / "scaler.pkl")

    X = scaler.transform(train_df[FEATURE_COLUMNS])

    # XGBoost's sklearn API needs integer class labels, not strings.
    # The encoder is saved alongside the model so predictions can be
    # mapped back to LOW/MEDIUM/HIGH consistently at evaluation time.
    encoder = LabelEncoder()
    y = encoder.fit_transform(train_df["label"])

    model = XGBClassifier(
        n_estimators=200, max_depth=6, learning_rate=0.1,
        random_state=42, eval_metric="mlogloss",
    )
    # XGBoost's sklearn API has no class_weight param (unlike RandomForest),
    # so severe class imbalance is corrected via per-sample weights instead.
    sample_weight = compute_sample_weight("balanced", y)
    model.fit(X, y, sample_weight=sample_weight)

    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, MODEL_PATH)
    joblib.dump(encoder, LABEL_ENCODER_PATH)
    print(f"XGBoost trained on {len(train_df)} windows. Saved to {MODEL_PATH}")


if __name__ == "__main__":
    main()
