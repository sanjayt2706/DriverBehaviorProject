"""
ML/src/step01_load_raw.py
Pipeline A, step 1 (Architecture.md Section 6): discover UAH-DriveSet trip
folders and their raw file paths.

Folder layout (docs/Dataset Specification.md):
    Dataset/raw/UAH-DriveSet/<DriverFolder>/<RouteFolder>/RAW_GPS.txt
                                             .../RAW_ACCELEROMETERS.txt
                                             .../EVENTS_INERTIAL.txt   (optional)

Route folder names encode metadata (date-distance-driver-behavior-road),
but exact formatting has drifted slightly across dataset mirrors, so this
matches on keywords rather than a strict format string - more robust to
naming variance than a rigid regex.
"""
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

ML_ROOT = Path(__file__).resolve().parent.parent
PROJECT_ROOT = ML_ROOT.parent
DATASET_ROOT = PROJECT_ROOT / "Dataset" / "raw" / "UAH-DriveSet"

BEHAVIORS = ["NORMAL", "DROWSY", "AGGRESSIVE"]
ROADS = ["MOTORWAY", "SECONDARY"]


@dataclass
class TripSource:
    trip_id: str
    driver: str
    behavior: str  # NORMAL / DROWSY / AGGRESSIVE / UNKNOWN
    road: str       # MOTORWAY / SECONDARY / UNKNOWN
    folder: Path
    gps_file: Path
    accel_file: Path
    events_file: Optional[Path]


def _match_keyword(name: str, keywords: List[str]) -> Optional[str]:
    upper = name.upper()
    for kw in keywords:
        if kw in upper:
            return kw
    return None


def discover_trips(dataset_root: Path = DATASET_ROOT) -> List[TripSource]:
    if not dataset_root.exists():
        raise FileNotFoundError(
            f"UAH-DriveSet not found at {dataset_root}. Download it from "
            "http://www.robesafe.uah.es/personal/eduardo.romera/uah-driveset/ "
            "and extract into Dataset/raw/UAH-DriveSet/ "
            "(see Documentation/Dataset Specification.md)."
        )

    trips: List[TripSource] = []
    for driver_dir in sorted(dataset_root.iterdir()):
        if not driver_dir.is_dir():
            continue
        for route_dir in sorted(driver_dir.iterdir()):
            if not route_dir.is_dir():
                continue

            gps_file = route_dir / "RAW_GPS.txt"
            accel_file = route_dir / "RAW_ACCELEROMETERS.txt"
            events_file = route_dir / "EVENTS_INERTIAL.txt"

            if not (gps_file.exists() and accel_file.exists()):
                continue  # incomplete route, skip

            behavior = _match_keyword(route_dir.name, BEHAVIORS) or "UNKNOWN"
            road = _match_keyword(route_dir.name, ROADS) or "UNKNOWN"

            trips.append(TripSource(
                trip_id=f"{driver_dir.name}_{route_dir.name}",
                driver=driver_dir.name,
                behavior=behavior,
                road=road,
                folder=route_dir,
                gps_file=gps_file,
                accel_file=accel_file,
                events_file=events_file if events_file.exists() else None,
            ))

    return trips


if __name__ == "__main__":
    for t in discover_trips():
        print(f"{t.trip_id}: driver={t.driver} behavior={t.behavior} road={t.road} events={'yes' if t.events_file else 'no'}")
