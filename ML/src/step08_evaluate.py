"""
ML/src/step08_evaluate.py
Pipeline A, step 8: evaluate both models (Architecture.md Section 6) -
accuracy, precision, recall, F1, confusion matrix, and 5-fold cross-
validation on the train split. Writes ML/outputs/model_comparison.json,
which is later copied into Backend/ml_model/ for the dashboard's Model
Comparison page.

5-fold CV is grouped by trip_id for the same leakage reason as the
train/test split in step05.
"""
import json
import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score, confusion_matrix,
)
from sklearn.model_selection import GroupKFold, cross_val_score
from sklearn.utils.class_weight import compute_sample_weight

ML_ROOT = Path(__file__).resolve().parent.parent
PROJECT_ROOT = ML_ROOT.parent
sys.path.insert(0, str(PROJECT_ROOT / "Backend"))
from app.config import ML_MODEL_DIR  # noqa: E402

sys.path.insert(0, str(ML_ROOT / "src"))
from step04_build_features import FEATURE_COLUMNS  # noqa: E402
from step05_split_scale import TRAIN_CSV, TEST_CSV  # noqa: E402
from step06_train_rf import MODEL_PATH as RF_PATH  # noqa: E402
from step07_train_xgb import MODEL_PATH as XGB_PATH, LABEL_ENCODER_PATH  # noqa: E402

OUTPUT_JSON = ML_ROOT / "outputs" / "model_comparison.json"
LABELS = ["LOW", "MEDIUM", "HIGH"]


def _metrics(y_true, y_pred) -> dict:
    return {
        "accuracy": accuracy_score(y_true, y_pred),
        "precision_macro": precision_score(y_true, y_pred, labels=LABELS, average="macro", zero_division=0),
        "recall_macro": recall_score(y_true, y_pred, labels=LABELS, average="macro", zero_division=0),
        "f1_macro": f1_score(y_true, y_pred, labels=LABELS, average="macro", zero_division=0),
        "confusion_matrix": confusion_matrix(y_true, y_pred, labels=LABELS).tolist(),
        "confusion_matrix_labels": LABELS,
    }


def _cv_f1(model_ctor, X, y, groups, n_splits=5, balanced_sample_weight=False) -> dict:
    n_splits = min(n_splits, len(set(groups)))
    if n_splits < 2:
        return {"mean_f1_macro": None, "note": "not enough trip groups for CV"}
    gkf = GroupKFold(n_splits=n_splits)

    if not balanced_sample_weight:
        scores = cross_val_score(
            model_ctor(), X, y, groups=groups, cv=gkf, scoring="f1_macro"
        )
        return {"mean_f1_macro": float(scores.mean()), "fold_scores": scores.tolist()}

    # cross_val_score has no version-stable way to fold-slice sample_weight,
    # so XGBoost (which needs per-sample weights instead of class_weight) is
    # cross-validated with an explicit GroupKFold loop instead.
    y_arr = np.asarray(y)
    scores = []
    for train_idx, val_idx in gkf.split(X, y_arr, groups=groups):
        model = model_ctor()
        weights = compute_sample_weight("balanced", y_arr[train_idx])
        model.fit(X[train_idx], y_arr[train_idx], sample_weight=weights)
        pred = model.predict(X[val_idx])
        scores.append(f1_score(y_arr[val_idx], pred, average="macro", zero_division=0))
    return {"mean_f1_macro": float(np.mean(scores)), "fold_scores": scores}


def main():
    train_df = pd.read_csv(TRAIN_CSV)
    test_df = pd.read_csv(TEST_CSV)
    scaler = joblib.load(ML_MODEL_DIR / "scaler.pkl")

    X_train = scaler.transform(train_df[FEATURE_COLUMNS])
    y_train = train_df["label"]
    X_test = scaler.transform(test_df[FEATURE_COLUMNS])
    y_test = test_df["label"]
    groups_train = train_df["trip_id"]

    results = {}

    # --- Random Forest ---
    rf = joblib.load(RF_PATH)
    rf_test_metrics = _metrics(y_test, rf.predict(X_test))
    from sklearn.ensemble import RandomForestClassifier
    rf_cv = _cv_f1(
        lambda: RandomForestClassifier(
            n_estimators=200, max_depth=12, class_weight="balanced", random_state=42
        ),
        X_train, y_train, groups_train,
    )
    results["RandomForest"] = {"test": rf_test_metrics, "cross_validation": rf_cv}

    # --- XGBoost ---
    xgb = joblib.load(XGB_PATH)
    encoder = joblib.load(LABEL_ENCODER_PATH)
    xgb_pred_encoded = xgb.predict(X_test)
    xgb_pred = encoder.inverse_transform(xgb_pred_encoded)
    xgb_test_metrics = _metrics(y_test, xgb_pred)

    from xgboost import XGBClassifier
    y_train_encoded = encoder.transform(y_train)
    xgb_cv = _cv_f1(
        lambda: XGBClassifier(n_estimators=200, max_depth=6, learning_rate=0.1,
                               random_state=42, eval_metric="mlogloss"),
        X_train, y_train_encoded, groups_train,
        balanced_sample_weight=True,
    )
    results["XGBoost"] = {"test": xgb_test_metrics, "cross_validation": xgb_cv}

    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_JSON.write_text(json.dumps(results, indent=2))

    for name, r in results.items():
        print(f"{name}: test F1_macro={r['test']['f1_macro']:.4f}  "
              f"CV F1_macro={r['cross_validation'].get('mean_f1_macro')}")
    print(f"Wrote {OUTPUT_JSON}")


if __name__ == "__main__":
    main()
