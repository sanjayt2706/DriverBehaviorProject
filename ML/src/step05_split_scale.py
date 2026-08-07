"""
ML/src/step05_split_scale.py
Pipeline A, step 5: 80/20 train/test split (Architecture.md Section 6),
GROUPED by trip_id so that overlapping windows from the same route never
appear in both sets. Splitting by window instead of by trip would leak
adjacent, 50%-overlap windows across train/test and inflate test accuracy -
this is a correctness fix, not an architecture change, since the split
ratio itself was already locked at 80/20.

Then fits StandardScaler on the train split ONLY (never on test) and
saves it + feature_list.json directly into Backend/ml_model/, per the
locked artifact path in Architecture.md.
"""
import json
import sys
from pathlib import Path

import joblib
import pandas as pd
from sklearn.model_selection import GroupShuffleSplit
from sklearn.preprocessing import StandardScaler

ML_ROOT = Path(__file__).resolve().parent.parent
PROJECT_ROOT = ML_ROOT.parent
sys.path.insert(0, str(PROJECT_ROOT / "Backend"))
from app.config import ML_MODEL_DIR  # noqa: E402  (reuse the locked artifact path)

sys.path.insert(0, str(ML_ROOT / "src"))
from step04_build_features import FEATURE_COLUMNS, OUTPUT_CSV  # noqa: E402

TRAIN_CSV = ML_ROOT / "outputs" / "train.csv"
TEST_CSV = ML_ROOT / "outputs" / "test.csv"


def main():
    df = pd.read_csv(OUTPUT_CSV)

    n_groups = df["trip_id"].nunique()
    if n_groups < 2:
        raise RuntimeError(
            f"Only {n_groups} distinct trip(s) in the dataset - need at least "
            "2 trips to form a trip-grouped train/test split."
        )

    splitter = GroupShuffleSplit(n_splits=1, test_size=0.2, random_state=42)
    train_idx, test_idx = next(splitter.split(df, groups=df["trip_id"]))
    train_df, test_df = df.iloc[train_idx], df.iloc[test_idx]

    scaler = StandardScaler()
    scaler.fit(train_df[FEATURE_COLUMNS])

    TRAIN_CSV.parent.mkdir(parents=True, exist_ok=True)
    train_df.to_csv(TRAIN_CSV, index=False)
    test_df.to_csv(TEST_CSV, index=False)

    ML_MODEL_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(scaler, ML_MODEL_DIR / "scaler.pkl")
    (ML_MODEL_DIR / "feature_list.json").write_text(json.dumps(FEATURE_COLUMNS, indent=2))

    print(f"Train: {len(train_df)} windows from {train_df['trip_id'].nunique()} trips")
    print(f"Test:  {len(test_df)} windows from {test_df['trip_id'].nunique()} trips")
    print(f"Saved scaler.pkl and feature_list.json to {ML_MODEL_DIR}")


if __name__ == "__main__":
    main()
