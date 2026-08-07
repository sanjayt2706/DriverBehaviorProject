"""
ML/src/analyze_class_distribution.py
Analyze class imbalance in the dataset and recommend balancing strategies.
"""
import json
import sys
from pathlib import Path
from collections import Counter

import pandas as pd
import numpy as np

ML_ROOT = Path(__file__).resolve().parent.parent
OUTPUTS = ML_ROOT / "outputs"

print("=" * 80)
print("CLASS DISTRIBUTION ANALYSIS")
print("=" * 80)

# Load the complete labeled dataset
features_csv = OUTPUTS / "dataset_features_labeled.csv"
if not features_csv.exists():
    print(f"✗ {features_csv} not found. Run steps 01-04 first.")
    sys.exit(1)

df = pd.read_csv(features_csv)
n_total = len(df)

print(f"\nComplete dataset: {n_total} windows")
print("-" * 80)

# Overall distribution
label_counts = df["label"].value_counts().sort_index()
print("\nOVERALL DISTRIBUTION (all data):")
for label in ["LOW", "MEDIUM", "HIGH"]:
    count = label_counts.get(label, 0)
    pct = 100 * count / n_total if n_total > 0 else 0
    bar = "█" * int(pct / 2)
    print(f"  {label:10} {count:6} samples ({pct:6.2f}%) {bar}")

# Train/test distribution
train_csv = OUTPUTS / "train.csv"
test_csv = OUTPUTS / "test.csv"

if train_csv.exists() and test_csv.exists():
    train_df = pd.read_csv(train_csv)
    test_df = pd.read_csv(test_csv)
    
    print(f"\nTRAIN SET DISTRIBUTION ({len(train_df)} windows, 80%):")
    train_counts = train_df["label"].value_counts().sort_index()
    for label in ["LOW", "MEDIUM", "HIGH"]:
        count = train_counts.get(label, 0)
        pct = 100 * count / len(train_df) if len(train_df) > 0 else 0
        bar = "█" * int(pct / 2)
        print(f"  {label:10} {count:6} samples ({pct:6.2f}%) {bar}")
    
    print(f"\nTEST SET DISTRIBUTION ({len(test_df)} windows, 20%):")
    test_counts = test_df["label"].value_counts().sort_index()
    for label in ["LOW", "MEDIUM", "HIGH"]:
        count = test_counts.get(label, 0)
        pct = 100 * count / len(test_df) if len(test_df) > 0 else 0
        bar = "█" * int(pct / 2)
        print(f"  {label:10} {count:6} samples ({pct:6.2f}%) {bar}")

# Imbalance metrics
print(f"\nIMBALANCE METRICS:")
print("-" * 80)
low = label_counts.get("LOW", 1)
med = label_counts.get("MEDIUM", 1)
high = label_counts.get("HIGH", 1)

print(f"\nRatio (HIGH : MEDIUM : LOW): {high} : {med} : {low}")

max_class = max(low, med, high)
min_class = min(low, med, high)
imbalance_ratio = max_class / min_class if min_class > 0 else float('inf')

print(f"Max/Min class ratio: {imbalance_ratio:.2f}x")

# Per-class imbalance ratios
print(f"\nPer-class ratios (normalized to max):")
print(f"  HIGH:   {high} ({100*high/max_class:6.1f}% of max)")
print(f"  MEDIUM: {med} ({100*med/max_class:6.1f}% of max)")
print(f"  LOW:    {low} ({100*low/max_class:6.1f}% of max)")

# Imbalance severity classification
print(f"\nIMBALANCE SEVERITY:")
print("-" * 80)
if imbalance_ratio < 1.5:
    severity = "MINIMAL"
    desc = "Classes are well-balanced."
elif imbalance_ratio < 3:
    severity = "MILD"
    desc = "Some imbalance but manageable with standard approaches."
elif imbalance_ratio < 10:
    severity = "MODERATE"
    desc = "Significant imbalance - balancing techniques recommended."
else:
    severity = "SEVERE"
    desc = "Severe imbalance - strong balancing measures required."

print(f"Severity: {severity} ({imbalance_ratio:.2f}x)")
print(f"Description: {desc}")

# Recommendation logic
print(f"\nBALANCING STRATEGY RECOMMENDATION:")
print("-" * 80)

recommendations = []

if imbalance_ratio >= 3:
    recommendations.append({
        "method": "class_weight='balanced'",
        "pros": [
            "✓ No data duplication needed",
            "✓ Works with any model (RF, XGBoost, etc.)",
            "✓ Requires no code changes - just a parameter",
            "✓ Recommended first step for any imbalance >= 3x",
        ],
        "cons": [
            "• Only adjusts loss function, doesn't create new training data",
            "• May not fully correct severe imbalance",
        ],
        "priority": "HIGH",
    })

if imbalance_ratio >= 5:
    recommendations.append({
        "method": "SMOTE (Synthetic Minority Oversampling)",
        "pros": [
            "✓ Generates synthetic minority samples in feature space",
            "✓ Addresses data scarcity without exact duplication",
            "✓ Preserves feature correlations",
            "✓ Better than naive oversampling",
        ],
        "cons": [
            "• Adds data volume - may increase training time",
            "• Can cause overfitting if combined with aggressive class_weight",
            "• Requires imblearn library installation",
            "• Only applied to training set (don't apply to test)",
        ],
        "priority": "MEDIUM",
    })

if imbalance_ratio >= 10:
    recommendations.append({
        "method": "Stratified oversampling of minority classes",
        "pros": [
            "✓ Simple to implement",
            "✓ Directly increases minority class representation",
            "✓ Fully controlled by you",
        ],
        "cons": [
            "• Creates exact duplicates - lower quality than SMOTE",
            "• Increases training data size and time",
            "• Can hurt generalization if not combined with regularization",
        ],
        "priority": "LOW (use SMOTE instead)",
    })

if imbalance_ratio >= 2:
    recommendations.append({
        "method": "Use macro F1 for model selection (do NOT use accuracy)",
        "pros": [
            "✓ Metrics matter more than the data",
            "✓ macro F1 already implemented in steps 08-09",
            "✓ Weights each class equally in evaluation",
        ],
        "cons": [
            "• Macro F1 can be unintuitive (one bad class sinks the score)",
        ],
        "priority": "CRITICAL",
    })

print("\nRECOMMENDED ACTIONS (in priority order):")
print()
for i, rec in enumerate(recommendations, 1):
    print(f"{i}. {rec['method'].upper()}")
    print(f"   Priority: {rec['priority']}")
    print(f"   Pros:")
    for pro in rec['pros']:
        print(f"     {pro}")
    print(f"   Cons:")
    for con in rec['cons']:
        print(f"     {con}")
    print()

# Next steps
print("IMPLEMENTATION NEXT STEPS:")
print("-" * 80)
print("""
1. IMMEDIATE (no retraining needed):
   ✓ Use macro F1 for evaluation (already in step 08-09)
   ✓ Review confusion matrix in model_comparison.json

2. IF IMBALANCE >= 3x (retraining required):
   → Add class_weight='balanced' to RandomForestClassifier (step06_train_rf.py)
   → Add scale_pos_weight or class_weight to XGBoost (step07_train_xgb.py)
   → Re-run steps 05-09

3. IF IMBALANCE >= 5x:
   → Consider SMOTE after the train/test split (new step 05b)
   → Only apply SMOTE to train split, evaluate on unbalanced test set
   → Retry models with class_weight + SMOTE combined

4. RUNTIME DEPLOYMENT:
   → Do NOT apply SMOTE to production data
   → Use the balanced model with confidence thresholds if needed
   → Monitor per-class accuracy on real trips (Android app)
""")

# Export analysis to JSON
analysis_output = {
    "dataset_size": n_total,
    "class_distribution": {
        "LOW": int(low),
        "MEDIUM": int(med),
        "HIGH": int(high),
    },
    "imbalance_ratio": float(imbalance_ratio),
    "severity": severity,
    "recommendations": [r["method"] for r in recommendations],
    "priority_actions": [r["method"] for r in recommendations if r["priority"] == "HIGH"],
}
(OUTPUTS / "class_distribution_analysis.json").write_text(json.dumps(analysis_output, indent=2))
print(f"✓ Analysis saved to {OUTPUTS / 'class_distribution_analysis.json'}")

print("\n" + "=" * 80)
