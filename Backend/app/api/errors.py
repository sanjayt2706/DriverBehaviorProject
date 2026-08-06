"""
Backend/app/api/errors.py
Error envelope shape locked in docs/API.md "Error format" section.
"""
from typing import Optional
from fastapi import HTTPException


class ApiError(HTTPException):
    def __init__(self, status_code: int, code: str, message: str, trip_id: Optional[str] = None):
        detail = {"error": {"code": code, "message": message}}
        if trip_id:
            detail["error"]["trip_id"] = trip_id
        super().__init__(status_code=status_code, detail=detail)


def trip_not_found(trip_id: str) -> ApiError:
    return ApiError(404, "TRIP_NOT_FOUND", f"Trip {trip_id} does not exist.", trip_id)


def trip_already_exists(trip_id: str) -> ApiError:
    return ApiError(409, "TRIP_ALREADY_EXISTS", f"Trip {trip_id} already exists.", trip_id)


def trip_not_processed(trip_id: str, status: str) -> ApiError:
    return ApiError(
        409, "TRIP_NOT_PROCESSED",
        f"Trip {trip_id} has status {status}. Call /process first.", trip_id,
    )


def invalid_trip_state(trip_id: str, status: str, expected: str) -> ApiError:
    return ApiError(
        409, "INVALID_TRIP_STATE",
        f"Trip {trip_id} has status {status}, expected {expected}.", trip_id,
    )


def batch_too_large(trip_id: str) -> ApiError:
    return ApiError(422, "BATCH_TOO_LARGE", "Batch exceeds 500 samples.", trip_id)


def insufficient_data(trip_id: str) -> ApiError:
    return ApiError(422, "INSUFFICIENT_DATA", "Not enough samples to form one window.", trip_id)


def processing_failed(trip_id: str, reason: str) -> ApiError:
    return ApiError(500, "PROCESSING_FAILED", reason, trip_id)
