"""
Backend/app/ml/loader.py
Layer 5. Loads best_model.pkl, scaler.pkl, feature_list.json ONCE at startup
(Architecture.md Section 4). If the artifacts don't exist yet (pre-training,
Days 1-4), falls back to a heuristic placeholder so the API contract stays
testable end-to-end before ML/ finishes training. Placeholder use is logged.
"""
import json
import logging

from app.config import MODEL_PATH, SCALER_PATH, FEATURE_LIST_PATH

logger = logging.getLogger("driverisk.ml")


class ModelBundle:
    def __init__(self):
        self.model = None
        self.scaler = None
        self.feature_list: list = []
        self.model_name = "PLACEHOLDER_HEURISTIC"
        self.loaded = False

    def load(self):
        if not (MODEL_PATH.exists() and SCALER_PATH.exists() and FEATURE_LIST_PATH.exists()):
            logger.warning(
                "ML artifacts not found in ml_model/. Running with a placeholder "
                "heuristic predictor until ML/export_artifacts.py produces "
                "best_model.pkl, scaler.pkl and feature_list.json."
            )
            return

        import joblib

        self.model = joblib.load(MODEL_PATH)
        self.scaler = joblib.load(SCALER_PATH)
        self.feature_list = json.loads(FEATURE_LIST_PATH.read_text())
        self.model_name = getattr(self.model, "algorithm_name", type(self.model).__name__)
        self.loaded = True
        logger.info(f"Loaded model {self.model_name} with {len(self.feature_list)} features.")


model_bundle = ModelBundle()
