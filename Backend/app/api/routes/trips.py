"""
Backend/app/api/routes/trips.py
Layer 3. The four locked endpoints (docs/API.md). No maths lives here -
this file orchestrates crud/, processing/, ml/ and explain/ only.
"""
import time
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.api import errors
from app.schemas.trip import CreateTripRequest, CreateTripResponse
from app.schemas.sensor import UploadBatchRequest, UploadBatchResponse
from app.schemas.result import ProcessResponse, TripResultResponse
from app.models.trip import TripStatus
from app.crud import trip as trip_crud
from app.crud import sensor as sensor_crud
from app.crud import result as result_crud
from app.processing.pipeline import run_pipeline
from app.ml.predictor import predict_window
from app.ml.aggregator import aggregate_trip
from app.explain.shap_explainer import explain_trip
from app.ml.loader import model_bundle
from app.config import MAX_BATCH_SIZE
from app.utils.time import utc_now_iso

router = APIRouter(prefix="/trips", tags=["trips"])


@router.post("", response_model=CreateTripResponse, status_code=201)
def create_trip(payload: CreateTripRequest, db: Session = Depends(get_db)):
    if trip_crud.get_trip(db, payload.trip_id):
        raise errors.trip_already_exists(payload.trip_id)

    trip = trip_crud.create_trip(
        db, payload.trip_id, payload.user_id, payload.device_model, payload.start_time
    )
    return CreateTripResponse(trip_id=trip.trip_id, status=trip.status, created_at=trip.created_at)


@router.post("/{trip_id}/upload", response_model=UploadBatchResponse)
def upload_batch(trip_id: str, payload: UploadBatchRequest, db: Session = Depends(get_db)):
    trip = trip_crud.get_trip(db, trip_id)
    if not trip:
        raise errors.trip_not_found(trip_id)
    if trip.status == TripStatus.PROCESSED:
        raise errors.invalid_trip_state(trip_id, trip.status, "UPLOADING or UPLOADED")
    if len(payload.samples) > MAX_BATCH_SIZE:
        raise errors.batch_too_large(trip_id)

    sensor_crud.bulk_insert_samples(db, trip_id, payload.samples)
    total = sensor_crud.count_samples(db, trip_id)

    is_last_batch = payload.batch_index == payload.batch_count - 1
    status = TripStatus.UPLOADED if is_last_batch else TripStatus.UPLOADING
    trip_crud.set_status(db, trip, status)
    trip_crud.set_end_time_and_count(db, trip, payload.end_time, total)

    return UploadBatchResponse(
        trip_id=trip_id,
        batch_index=payload.batch_index,
        received=len(payload.samples),
        total_samples=total,
        status=status,
    )


@router.post("/{trip_id}/process", response_model=ProcessResponse)
def process_trip(trip_id: str, db: Session = Depends(get_db)):
    trip = trip_crud.get_trip(db, trip_id)
    if not trip:
        raise errors.trip_not_found(trip_id)
    if trip.status not in (TripStatus.UPLOADED, TripStatus.PROCESSED):
        raise errors.invalid_trip_state(trip_id, trip.status, "UPLOADED")

    trip_crud.set_status(db, trip, TripStatus.PROCESSING)
    start = time.time()
    agg = None

    try:
        raw_samples = sensor_crud.get_samples_ordered(db, trip_id)
        pipeline_out = run_pipeline(raw_samples)
        feature_rows = pipeline_out["feature_rows"]

        if not feature_rows:
            raise errors.insufficient_data(trip_id)

        for row in feature_rows:
            label, confidence = predict_window(row)
            row["predicted_label"] = label
            row["predicted_confidence"] = confidence

        result_crud.clear_previous_results(db, trip_id)
        result_crud.save_features(db, trip_id, feature_rows)

        agg = aggregate_trip(feature_rows)
        agg["model_name"] = model_bundle.model_name
        agg["model_version"] = None
        result_crud.save_prediction(db, trip_id, agg)

        factors = explain_trip(feature_rows)
        result_crud.save_shap_explanations(db, trip_id, factors)

        trip.duration_s = pipeline_out["duration_s"]
        trip.distance_km = pipeline_out["distance_km"]
        trip.processed_at = utc_now_iso()
        db.commit()

        trip_crud.set_status(db, trip, TripStatus.PROCESSED)

    except errors.ApiError:
        trip_crud.set_status(db, trip, TripStatus.FAILED)
        raise
    except Exception as e:
        trip_crud.set_status(db, trip, TripStatus.FAILED)
        raise errors.processing_failed(trip_id, str(e))

    processing_time_ms = int((time.time() - start) * 1000)
    return ProcessResponse(
        trip_id=trip_id,
        status=TripStatus.PROCESSED,
        trip_score=agg["trip_score"],
        risk_level=agg["risk_level"],
        window_count=agg["window_count"],
        processing_time_ms=processing_time_ms,
    )


@router.get("/{trip_id}/result", response_model=TripResultResponse)
def get_result(trip_id: str, db: Session = Depends(get_db)):
    trip = trip_crud.get_trip(db, trip_id)
    if not trip:
        raise errors.trip_not_found(trip_id)
    if trip.status != TripStatus.PROCESSED:
        raise errors.trip_not_processed(trip_id, trip.status)

    return result_crud.build_result(db, trip)
