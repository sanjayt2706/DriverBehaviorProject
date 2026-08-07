#!/bin/bash
# ML/run_diagnostics.sh
# Run all diagnostic scripts and generate the complete training summary

set -e

ML_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ML_ROOT"

echo "╔════════════════════════════════════════════════════════════════════════════╗"
echo "║                    ML TRAINING SUMMARY - FULL DIAGNOSTIC                  ║"
echo "╚════════════════════════════════════════════════════════════════════════════╝"

# 1. General diagnostic
echo ""
echo "Step 1: General Pipeline Diagnostic"
echo "────────────────────────────────────────────────────────────────────────────"
python3 src/ml_diagnostic.py

# 2. Feature parity verification
echo ""
echo "Step 2: Feature Parity Verification"
echo "────────────────────────────────────────────────────────────────────────────"
python3 src/verify_feature_parity.py

# 3. Class distribution analysis
echo ""
echo "Step 3: Class Distribution Analysis"
echo "────────────────────────────────────────────────────────────────────────────"
python3 src/analyze_class_distribution.py

# 4. Regenerate SHAP if needed
echo ""
echo "Step 4: SHAP Feature Importance (checking for completeness)"
echo "────────────────────────────────────────────────────────────────────────────"
if [ -f "outputs/shap_global_importance.json" ]; then
    SHAP_COUNT=$(python3 -c "import json; f=json.load(open('outputs/shap_global_importance.json')); print(len(f.get('importance', [])))")
    if [ "$SHAP_COUNT" -lt 24 ]; then
        echo "⚠ SHAP output incomplete ($SHAP_COUNT/24 features), regenerating..."
        python3 src/step10_global_shap_fixed.py
    else
        echo "✓ SHAP output complete ($SHAP_COUNT features)"
    fi
else
    echo "✗ SHAP output not found, regenerating..."
    python3 src/step10_global_shap_fixed.py
fi

# 5. Generate summary
echo ""
echo "Step 5: Generate Complete Training Summary"
echo "────────────────────────────────────────────────────────────────────────────"
python3 src/generate_training_summary.py

echo ""
echo "╔════════════════════════════════════════════════════════════════════════════╗"
echo "║                           DIAGNOSTIC COMPLETE                             ║"
echo "╚════════════════════════════════════════════════════════════════════════════╝"
echo ""
echo "Output files generated:"
echo "  • ML/ML_Training_Summary.md - Complete training summary (see below)"
echo "  • ML/outputs/class_distribution_analysis.json"
echo "  • ML/outputs/shap_global_importance.json (all 24 features)"
echo ""
echo "Summary content:"
if [ -f "ML_Training_Summary.md" ]; then
    wc -l ML_Training_Summary.md
    echo ""
    echo "Preview (first 50 lines):"
    head -50 ML_Training_Summary.md
fi
