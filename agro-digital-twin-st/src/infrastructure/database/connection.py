"""
Database Connection & SQLAlchemy Session Management for AgroTwin-AI.
Supports PostgreSQL via DATABASE_URL with automatic, graceful fallback
to local SQLite (sqlite:///data/agrotwin.db).
"""

import os
import logging
from typing import Generator, Optional
from datetime import datetime

from sqlalchemy import (
    create_engine,
    Column,
    String,
    Integer,
    Float,
    Boolean,
    DateTime,
    Text,
    JSON
)
from sqlalchemy.orm import declarative_base, sessionmaker, Session

logger = logging.getLogger(__name__)

Base = declarative_base()


class UserORM(Base):
    __tablename__ = "users"

    id = Column(String(64), primary_key=True)
    username = Column(String(64), unique=True, nullable=False, index=True)
    email = Column(String(128), unique=True, nullable=False)
    password_hash = Column(String(256), nullable=False)
    role = Column(String(32), nullable=False, default="GUEST")  # ADMIN, RESEARCHER, ANALYST, GUEST
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class WatershedORM(Base):
    __tablename__ = "watersheds"

    id = Column(String(64), primary_key=True)
    name = Column(String(128), nullable=False)
    basin_name = Column(String(128), nullable=False)
    area_km2 = Column(Float, nullable=False)
    outlet_lat = Column(Float, nullable=False)
    outlet_lon = Column(Float, nullable=False)
    state = Column(String(64), default="Iowa")
    description = Column(Text, default="")


class TrainingRunORM(Base):
    __tablename__ = "training_runs"

    id = Column(String(64), primary_key=True)
    user_id = Column(String(64), nullable=True)
    target_name = Column(String(64), nullable=False)
    learning_mode = Column(String(32), nullable=False)
    validation_strategy = Column(String(64), nullable=False)
    fast_dev_mode = Column(Boolean, default=False)
    status = Column(String(32), default="COMPLETED")
    duration_seconds = Column(Float, nullable=True)
    champion_model_name = Column(String(128), nullable=True)
    champion_metrics = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class PredictionLogORM(Base):
    __tablename__ = "prediction_logs"

    id = Column(String(64), primary_key=True)
    target_name = Column(String(64), nullable=False)
    learning_mode = Column(String(32), nullable=False)
    model_used = Column(String(128), nullable=False)
    predicted_value = Column(Float, nullable=False)
    baseline_value = Column(Float, nullable=True)
    residual_value = Column(Float, nullable=True)
    unit = Column(String(32), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


# Global Engine & Session Factory
_engine = None
_SessionFactory = None


def get_database_url() -> str:
    """Retrieves DATABASE_URL from env or defaults to local SQLite."""
    url = os.getenv("DATABASE_URL")
    if url:
        # SQLAlchemy 1.4+ compatibility for postgres:// -> postgresql://
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql://", 1)
        return url

    # Local SQLite fallback
    data_dir = os.path.join(os.getcwd(), "data")
    os.makedirs(data_dir, exist_ok=True)
    sqlite_path = os.path.join(data_dir, "agrotwin.db")
    return f"sqlite:///{sqlite_path}"


def get_engine():
    """Initializes and returns the singleton SQLAlchemy engine."""
    global _engine
    if _engine is None:
        db_url = get_database_url()
        try:
            if "sqlite" in db_url:
                _engine = create_engine(db_url, connect_args={"check_same_thread": False})
            else:
                _engine = create_engine(db_url, pool_pre_ping=True)
            logger.info(f"Connected to database engine: {db_url.split('@')[-1] if '@' in db_url else db_url}")
        except Exception as e:
            logger.warning(f"Failed to connect using {db_url}: {e}. Falling back to in-memory SQLite.")
            _engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    return _engine


def get_session_factory():
    """Returns singleton SessionMaker."""
    global _SessionFactory
    if _SessionFactory is None:
        engine = get_engine()
        _SessionFactory = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return _SessionFactory


def get_db_session() -> Generator[Session, None, None]:
    """Yields a database session with automatic commit/rollback."""
    factory = get_session_factory()
    session = factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def init_db():
    """Creates database tables if they do not exist."""
    engine = get_engine()
    Base.metadata.create_all(bind=engine)
