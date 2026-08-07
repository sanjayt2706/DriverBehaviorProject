"""
ML/src/step03_label.py
Pipeline A, step 3: assign a LOW/MEDIUM/HIGH ground-truth label to each
window (locked label vocabulary, Architecture.md Section 1).

UAH-DriveSet's EVENTS_INERTIAL file gives per-event timestamps and a
severity level (1=low, 2=medium, 3=high) for braking, turning and
acceleration events, produced by DriveSafe's own maneuver detector - this
is real per-event ground truth, not a label we are inventing. A window is
labeled by the highest-severity event whose timestamp falls inside it:

    no event lands in the window      -> LOW
    highest event level in window 1   -> LOW
    highest event level in window 2   -> MEDIUM
    highest event level in window 3   -> HIGH

If a route has no EVENTS_INERTIAL file at all, there is no per-event
ground truth for it, so every window in that route falls back to the
trip's overall behavior label from the folder name:
    NORMAL -> LOW, DROWSY -> MEDIUM, AGGRESSIVE -> HIGH
This fallback is coarser (one label for the whole trip) and is only used
when the per-event file is genuinely missing, not as a general default -
see Documentation/Dataset Specification.md for the reasoning.
"""
from pathlib import Path
from typing import List, Optional

_LEVEL_TO_RISK = {1: "LOW", 2: "MEDIUM", 3: "HIGH"}
_BEHAVIOR_TO_RISK = {"NORMAL": "LOW", "DROWSY": "MEDIUM", "AGGRESSIVE": "HIGH"}


def _load_events(events_file: Path) -> List[dict]:
    """EVENTS_INERTIAL.txt columns: timestamp(s), type, level(1-3), lat, lon, date."""
    events = []
    for line in events_file.read_text().splitlines():
        parts = line.strip().split()
        if len(parts) < 3:
            continue
        ts_s, ev_type, level = float(parts[0]), int(float(parts[1])), int(float(parts[2]))
        events.append({"t": ts_s, "type": ev_type, "level": level})
    return events


def label_windows(
    windows: List[List[dict]],
    events_file: Optional[Path],
    fallback_behavior: str,
) -> List[str]:
    """
    windows: output of app.processing.windowing.make_windows() - each
             window is a list of sample dicts with a 'timestamp' key (ms).
    Returns one label per window, in the same order as `windows`.
    """
    if events_file is None:
        return [_BEHAVIOR_TO_RISK.get(fallback_behavior, "LOW")] * len(windows)

    events = _load_events(events_file)

    labels = []
    for window in windows:
        if not window:
            labels.append("LOW")
            continue

        w_start_ms = window[0]["timestamp"]
        w_end_ms = window[-1]["timestamp"]

        max_level = 0
        for ev in events:
            ev_ms = ev["t"] * 1000
            if w_start_ms <= ev_ms <= w_end_ms:
                max_level = max(max_level, ev["level"])

        labels.append(_LEVEL_TO_RISK.get(max_level, "LOW"))

    return labels
