"""
Backend/app/config.py

Central configuration. Values here correspond to the locked parameters in
docs/Architecture.md - window size, overlap, thresholds, aggregation weights.
Do not hardcode these numbers anywhere else in the codebase.
"""
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent  # Backend/

# --- Database ---
DATABASE_PATH = BASE_DIR / "driverisk.db"
DATABASE_URL = f"sqlite:///{DATABASE_PATH}"

# --- Model artifacts (Architecture.md locked path) ---
ML_MODEL_DIR = BASE_DIR / "ml_model"
MODEL_PATH = ML_MODEL_DIR / "best_model.pkl"
SCALER_PATH = ML_MODEL_DIR / "scaler.pkl"
FEATURE_LIST_PATH = ML_MODEL_DIR / "feature_list.json"
MODEL_COMPARISON_PATH = ML_MODEL_DIR / "model_comparison.json"

# --- Windowing (Architecture.md Layer 4, locked) ---
WINDOW_SECONDS = 5.0
WINDOW_OVERLAP = 0.5  # 50%
IMU_HZ = 50
GPS_HZ = 1
MIN_SAMPLES_PER_WINDOW = int(WINDOW_SECONDS * IMU_HZ * 0.5)  # tolerate some gaps

# --- Upload batching (API.md locked) ---
MAX_BATCH_SIZE = 500

# --- Trip score aggregation (Architecture.md Section 14 not yet written) ---
# [INFERRED - approved as default 2026-08-06, revisit if Section 14 finalises differently]
AGG_WEIGHT_W1 = 1.0  # weight on %HIGH windows
AGG_WEIGHT_W2 = 0.4  # weight on %MEDIUM windows

RISK_LOW_THRESHOLD = 70     # trip_score >= 70          -> LOW
RISK_MEDIUM_THRESHOLD = 40  # 40 <= trip_score < 70      -> MEDIUM
                             # trip_score < 40            -> HIGH

# --- Event thresholds used by processing/features.py ---
# [INFERRED - placeholder values, must be tuned against real drive data
#  once ML/ collects the dataset described in Architecture.md Section 6]
HARSH_BRAKE_THRESHOLD_MS2 = -3.0     # accel_x below this = harsh brake
HARSH_ACCEL_THRESHOLD_MS2 = 3.0      # accel_x above this = harsh acceleration
HARSH_CORNER_GYRO_THRESHOLD = 0.35   # |gyro_z| above this = harsh corner (rad/s)
OVERSPEED_KMH = 80.0                 # flat placeholder; road-type aware later

# --- Curve density (Architecture.md D1 novelty) ---
CURVE_HEADING_CHANGE_DEG = 15.0  # heading change counted as "a curve"
