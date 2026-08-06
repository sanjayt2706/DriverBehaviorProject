"""
Backend/app/database.py

SQLAlchemy engine + session setup for the single SQLite file driverisk.db.
Enables WAL mode and foreign key enforcement per Database.md "Operational
notes" - WAL lets Streamlit read the file while FastAPI writes to it.
"""
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, declarative_base

from app.config import DATABASE_URL

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
)


@event.listens_for(engine, "connect")
def _set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.close()


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Create all tables if they don't exist. Called once at startup."""
    from app.models import trip, raw_sensor_data, feature, prediction, shap_explanation  # noqa: F401
    Base.metadata.create_all(bind=engine)
