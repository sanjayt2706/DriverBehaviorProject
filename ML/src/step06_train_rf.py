"""
ML/src/step06_train_rf.py
Pipeline A, step 6: train Random Forest with the locked hyperparameters
(Architecture.md Section 6): n_estimators=200, max_depth=12.
"""
import sys
from pathlib import Path

import joblib
import pandas as pd
from sklearn.ensemble import RandomForestClassifier

ML_ROOT = Path(__file__).resolve().parent.parent
PROJECT_ROOT = ML_ROOT.parent
sys.path.insert(0, str(PROJECT_ROOT / "Backend"))
from app.config import ML_MODEL_DIR  # noqa: E402

sys.path.insert(0, str(ML_ROOT / "src"))
from step04_build_features import FEATURE_COLUMNS  # noqa: E402
from step05_split_scale import TRAIN_CSV  # noqa: E402

MODEL_PATH = ML_ROOT / "outputs" / "rf_model.pkl"


def main():
    train_df = pd.read_csv(TRAIN_CSV)
    scaler = joblib.load(ML_MODEL_DIR / "scaler.pkl")

    X = scaler.transform(train_df[FEATURE_COLUMNS])
    y = train_df["label"]

    model = RandomForestClassifier(
        n_estimators=200, max_depth=12, class_weight="balanced", random_state=42
    )
    model.fit(X, y)

    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, MODEL_PATH)
    print(f"Random Forest trained on {len(train_df)} windows. Saved to {MODEL_PATH}")


if __name__ == "__main__":
    main()
