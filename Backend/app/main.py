"""
Backend/app/main.py
FastAPI entrypoint. Loads the ML model bundle once at startup and creates
the SQLite schema if it doesn't exist yet (Architecture.md Layer 3).
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import init_db
from app.ml.loader import model_bundle
from app.api.routes.trips import router as trips_router

logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    model_bundle.load()
    yield


app = FastAPI(title="DriveRisk API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten before any real deployment
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(trips_router)


@app.get("/health")
def health():
    return {
        "status": "ok",
        "model_loaded": model_bundle.loaded,
        "model_name": model_bundle.model_name,
    }
