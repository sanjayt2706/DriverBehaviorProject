"""
Backend/app/ml/model_wrapper.py
Layer 5. RandomForestClassifier predicts LOW/MEDIUM/HIGH strings natively,
but XGBoost's sklearn API requires integer-encoded labels internally and
returns integers from predict() - confirmed empirically against the
installed xgboost version, not assumed.

Rather than teach predictor.py which algorithm won the comparison, the
training pipeline (ML/src/step09_select_best.py) wraps whichever model
wins in this class before saving it as best_model.pkl. Backend/app/ml/
never needs to know or care which algorithm is inside - it always gets
predict() -> string label and predict_proba() -> probability array.

This class must be imported from this exact module path (app.ml.model_wrapper)
on both sides - by the training pipeline when the model is pickled, and by
Backend/app/ml/loader.py when it's unpickled - or joblib/pickle cannot
resolve the class.
"""
from typing import Optional


class LabelDecodingClassifier:
    def __init__(self, model, label_encoder: Optional[object] = None, algorithm_name: str = ""):
        self.model = model
        # None for models that predict string labels natively (RandomForest).
        # Set for models that needed integer-encoded labels internally (XGBoost).
        self.label_encoder = label_encoder
        # "RandomForest" / "XGBoost" - kept explicit so model_name in the API
        # response and predictions.model_name in the DB say the real
        # algorithm rather than "LabelDecodingClassifier".
        self.algorithm_name = algorithm_name or type(model).__name__

    def predict(self, X):
        raw = self.model.predict(X)
        if self.label_encoder is not None:
            return self.label_encoder.inverse_transform(raw)
        return raw

    def predict_proba(self, X):
        return self.model.predict_proba(X)

    @property
    def classes_(self):
        if self.label_encoder is not None:
            return self.label_encoder.classes_
        return self.model.classes_
