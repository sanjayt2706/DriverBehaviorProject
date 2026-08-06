"""
Backend/app/processing/windowing.py
Layer 4, step 2: sliding window segmentation.
5 s windows, 50% overlap - locked in Architecture.md Sections 4 and 6.
"""
from typing import List, Dict
from app.config import WINDOW_SECONDS, WINDOW_OVERLAP, MIN_SAMPLES_PER_WINDOW


def make_windows(samples: List[Dict]) -> List[List[Dict]]:
    """
    Splits cleaned samples (ordered by timestamp, ms) into overlapping windows.
    Window length and step are computed from wall-clock time rather than
    sample count, since a real drive's sample rate is never exactly 50 Hz.
    """
    if not samples:
        return []

    window_ms = int(WINDOW_SECONDS * 1000)
    step_ms = int(window_ms * (1 - WINDOW_OVERLAP))

    start_ts = samples[0]["timestamp"]
    end_ts = samples[-1]["timestamp"]

    windows: List[List[Dict]] = []
    w_start = start_ts
    while w_start + window_ms <= end_ts + step_ms:
        w_end = w_start + window_ms
        window = [s for s in samples if w_start <= s["timestamp"] < w_end]
        if len(window) >= MIN_SAMPLES_PER_WINDOW:
            windows.append(window)
        w_start += step_ms

    return windows
