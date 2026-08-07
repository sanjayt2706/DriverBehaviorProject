"""
ML/src/export_artifacts.py
Pipeline A, final step: verify the 4 locked artifacts (Architecture.md
Section 6) are present in Backend/ml_model/. steps 05 and 09 already write
directly into that folder (scaler.pkl + feature_list.json in step05,
best_model.pkl + model_comparison.json in step09) rather than writing to
ML/outputs/ and copying afterward - this avoids a class of "trained but
forgot to copy" bugs. This script is the final checkpoint before telling
Backend to pick the model up.
"""
import sys
from pathlib import Path

ML_ROOT = Path(__file__).resolve().parent.parent
PROJECT_ROOT = ML_ROOT.parent
sys.path.insert(0, str(PROJECT_ROOT / "Backend"))
from app.config import MODEL_PATH, SCALER_PATH, FEATURE_LIST_PATH, MODEL_COMPARISON_PATH  # noqa: E402

REQUIRED = {
    "best_model.pkl": MODEL_PATH,
    "scaler.pkl": SCALER_PATH,
    "feature_list.json": FEATURE_LIST_PATH,
    "model_comparison.json": MODEL_COMPARISON_PATH,
}


def main():
    missing = [name for name, path in REQUIRED.items() if not path.exists()]
    if missing:
        print("MISSING artifacts:", missing)
        print("Run steps 04 through 09 first (see ML/README.md).")
        sys.exit(1)

    print("All artifacts present in Backend/ml_model/:")
    for name, path in REQUIRED.items():
        size_kb = path.stat().st_size / 1024
        print(f"  {name}: {size_kb:.1f} KB")

    print("\nBackend will pick these up automatically on next startup.")
    print("Confirm with: GET /health -> model_loaded should be true.")


if __name__ == "__main__":
    main()
