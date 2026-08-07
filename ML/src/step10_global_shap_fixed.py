"""
ML/src/step10_global_shap_fixed.py
Compute global SHAP feature importance for multiclass RandomForest.
Handles SHAP 0.52+ API which returns Explanation objects.
Aggregates feature importance across all classes to produce one global value per feature.
"""
import json
import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import shap

ML_ROOT = Path(__file__).resolve().parent.parent
PROJECT_ROOT = ML_ROOT.parent
sys.path.insert(0, str(PROJECT_ROOT / "Backend"))
from app.config import ML_MODEL_DIR  # noqa: E402

sys.path.insert(0, str(ML_ROOT / "src"))
from step04_build_features import FEATURE_COLUMNS  # noqa: E402
from step05_split_scale import TEST_CSV  # noqa: E402

# Paths
BEST_MODEL_PATH = ML_MODEL_DIR / "best_model.pkl"
SCALER_PATH = ML_MODEL_DIR / "scaler.pkl"

OUTPUT_JSON = ML_ROOT / "outputs" / "shap_global_importance.json"
OUTPUT_PNG = ML_ROOT / "outputs" / "shap_global_importance.png"


def extract_shap_values(raw_model, X_test):
    """
    Extract SHAP values from TreeExplainer output.
    Handles SHAP 0.52+ Explanation object format.
    Returns: (shap_values, base_value)
      - shap_values: ndarray of shape (n_samples, n_features) or (n_samples, n_features, n_classes)
      - base_value: scalar or array
    """
    print(f"  Creating TreeExplainer for {type(raw_model).__name__}...")
    explainer = shap.TreeExplainer(raw_model)
    
    print(f"  Computing SHAP values on {len(X_test)} test samples...")
    explanation = explainer(X_test)
    
    # SHAP 0.52+ returns Explanation object
    # Access .values and .base_values attributes
    if hasattr(explanation, 'values'):
        shap_values = explanation.values
    else:
        shap_values = explanation
    
    if hasattr(explanation, 'base_values'):
        base_value = explanation.base_values
    else:
        base_value = explainer.expected_value
    
    print(f"  SHAP values shape: {shap_values.shape}")
    print(f"  SHAP values dtype: {shap_values.dtype}")
    
    return shap_values, base_value


def aggregate_multiclass_importance(shap_values, n_features):
    """
    Aggregate SHAP values across classes to get one importance per feature.
    
    Handles three cases:
    1. Binary classification: shap_values is (n_samples, n_features)
       → Use absolute values, average across samples
    2. Multiclass (3 classes): shap_values is (n_samples, n_features, n_classes)
       → Average absolute SHAP across classes, then across samples
    3. Multiclass as list: shap_values is list of arrays
       → Same logic as case 2
    """
    print(f"\n  Input shape: {np.array(shap_values).shape}")
    
    # Case 1: List of arrays (one per class)
    if isinstance(shap_values, list):
        print(f"  Detected: List of {len(shap_values)} SHAP arrays (one per class)")
        # Stack to (n_classes, n_samples, n_features), then permute to (n_samples, n_classes, n_features)
        stacked = np.stack(shap_values, axis=0)  # (n_classes, n_samples, n_features)
        shap_values = np.transpose(stacked, (1, 2, 0))  # (n_samples, n_features, n_classes)
        print(f"  Reshaped to: {shap_values.shape}")
    
    # Case 2: 3D array (n_samples, n_features, n_classes)
    if shap_values.ndim == 3:
        print(f"  Detected: Multiclass output (3D array)")
        print(f"    Samples: {shap_values.shape[0]}, Features: {shap_values.shape[1]}, Classes: {shap_values.shape[2]}")
        # Average absolute SHAP across classes (axis 2), then across samples (axis 0)
        mean_abs = np.abs(shap_values).mean(axis=2).mean(axis=0)
    
    # Case 3: 2D array (n_samples, n_features) - binary or single output
    elif shap_values.ndim == 2:
        print(f"  Detected: Binary or single-output (2D array)")
        print(f"    Samples: {shap_values.shape[0]}, Features: {shap_values.shape[1]}")
        mean_abs = np.abs(shap_values).mean(axis=0)
    
    else:
        raise ValueError(f"Unexpected SHAP shape: {shap_values.shape}")
    
    # Verify we got one value per feature
    if len(mean_abs) != n_features:
        raise ValueError(f"Got {len(mean_abs)} importance values but expected {n_features} features")
    
    print(f"  Output: One importance value per feature (length={len(mean_abs)})")
    return mean_abs


def main():
    print("Step 10: Global SHAP Importance (Fixed Multiclass Handling)")
    print("=" * 80)
    
    print(f"\nFeature list: {len(FEATURE_COLUMNS)} features")
    for i, feat in enumerate(FEATURE_COLUMNS, 1):
        if i <= 5 or i > len(FEATURE_COLUMNS) - 3:
            print(f"  {i:2}. {feat}")
        elif i == 6:
            print(f"  ... ({len(FEATURE_COLUMNS) - 8} more features) ...")
    
    # Load the best model
    if not BEST_MODEL_PATH.exists():
        print(f"✗ Model not found at {BEST_MODEL_PATH}")
        sys.exit(1)
    
    print(f"\nLoading model from {BEST_MODEL_PATH}...")
    loaded_model = joblib.load(BEST_MODEL_PATH)
    model_name = getattr(loaded_model, "algorithm_name", type(loaded_model).__name__)
    # best_model.pkl stores a LabelDecodingClassifier wrapper (see
    # Backend/app/ml/model_wrapper.py); TreeExplainer needs the raw
    # sklearn/xgboost estimator underneath it, not the wrapper.
    raw_model = getattr(loaded_model, "model", loaded_model)
    print(f"✓ Model loaded: {model_name}")
    
    # Load test data
    print(f"\nLoading test data from {TEST_CSV}...")
    test_df = pd.read_csv(TEST_CSV)
    scaler = joblib.load(SCALER_PATH)
    X_test = scaler.transform(test_df[FEATURE_COLUMNS])
    print(f"✓ Test data loaded: {X_test.shape}")
    
    # Compute SHAP values
    print(f"\nComputing SHAP importance...")
    shap_values, base_value = extract_shap_values(raw_model, X_test)
    
    # Aggregate across classes
    print(f"\nAggregating importance across classes...")
    mean_abs = aggregate_multiclass_importance(shap_values, len(FEATURE_COLUMNS))
    
    # Rank by importance
    importance = sorted(
        zip(FEATURE_COLUMNS, mean_abs.tolist()), 
        key=lambda kv: kv[1], 
        reverse=True
    )
    
    print(f"\n✓ All {len(importance)} features ranked by importance:")
    print(f"\nTop 10:")
    for rank, (fname, fval) in enumerate(importance[:10], 1):
        print(f"  {rank:2}. {fname:35} {fval:10.6f}")
    
    # Write JSON
    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    output_data = {
        "model": model_name,
        "shap_version": shap.__version__,
        "n_features": len(importance),
        "importance": [
            {"feature": f, "mean_abs_shap": v, "rank": i} 
            for i, (f, v) in enumerate(importance, 1)
        ]
    }
    OUTPUT_JSON.write_text(json.dumps(output_data, indent=2))
    print(f"\n✓ Saved complete ranking to {OUTPUT_JSON}")
    
    # Plot all features
    names, values = zip(*importance)
    plt.figure(figsize=(10, max(6, len(names) * 0.25)))
    plt.barh(names[::-1], values[::-1], color="steelblue")
    plt.xlabel("Mean |SHAP value|")
    plt.ylabel("Feature")
    plt.title(f"Global feature importance - all {len(names)} features ({model_name})")
    plt.tight_layout()
    plt.savefig(OUTPUT_PNG, dpi=120, bbox_inches="tight")
    print(f"✓ Saved plot to {OUTPUT_PNG}")
    
    print("\n" + "=" * 80)
    print("SUMMARY: Top 20 features")
    print("=" * 80)
    for rank, (fname, fval) in enumerate(importance[:20], 1):
        print(f"{rank:2}. {fname:35} {fval:10.6f}")
    
    print("\n✓ SUCCESS: Generated all 24 features ranked by SHAP importance")


if __name__ == "__main__":
    main()