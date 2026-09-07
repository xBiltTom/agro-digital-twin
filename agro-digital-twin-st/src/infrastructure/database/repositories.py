"""
Repository Implementations for SQLAlchemy / PostgreSQL Persistence.
Decouples Streamlit and application logic from raw SQL queries.
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from datetime import datetime
import uuid

from .models import (
    UserRecord,
    WatershedRecord,
    TrainingRunRecord,
    TrainedModelRecord,
    PredictionRecord,
    ReportRecord,
    UserRole
)
from .connection import (
    get_session_factory,
    UserORM,
    WatershedORM,
    TrainingRunORM,
    PredictionLogORM
)


class IUserRepository(ABC):
    @abstractmethod
    def get_by_id(self, user_id: str) -> Optional[UserRecord]:
        pass

    @abstractmethod
    def get_by_username(self, username: str) -> Optional[UserRecord]:
        pass

    @abstractmethod
    def create(self, user: UserRecord) -> UserRecord:
        pass


class SQLAlchemyUserRepository(IUserRepository):
    def __init__(self):
        self.session_factory = get_session_factory()

    def get_by_id(self, user_id: str) -> Optional[UserRecord]:
        with self.session_factory() as session:
            row = session.query(UserORM).filter(UserORM.id == user_id).first()
            if not row:
                return None
            return UserRecord(
                id=row.id,
                username=row.username,
                email=row.email,
                password_hash=row.password_hash,
                role=UserRole(row.role),
                created_at=row.created_at,
                is_active=row.is_active
            )

    def get_by_username(self, username: str) -> Optional[UserRecord]:
        with self.session_factory() as session:
            row = session.query(UserORM).filter(UserORM.username == username).first()
            if not row:
                return None
            return UserRecord(
                id=row.id,
                username=row.username,
                email=row.email,
                password_hash=row.password_hash,
                role=UserRole(row.role),
                created_at=row.created_at,
                is_active=row.is_active
            )

    def create(self, user: UserRecord) -> UserRecord:
        with self.session_factory() as session:
            orm_user = UserORM(
                id=user.id or str(uuid.uuid4()),
                username=user.username,
                email=user.email,
                password_hash=user.password_hash,
                role=user.role.value if isinstance(user.role, UserRole) else str(user.role),
                is_active=user.is_active,
                created_at=user.created_at or datetime.utcnow()
            )
            session.add(orm_user)
            session.commit()
            return user


class ITrainingRunRepository(ABC):
    @abstractmethod
    def save_run(self, run: TrainingRunRecord) -> TrainingRunRecord:
        pass

    @abstractmethod
    def list_recent_runs(self, limit: int = 10) -> List[TrainingRunRecord]:
        pass


class SQLAlchemyTrainingRunRepository(ITrainingRunRepository):
    def __init__(self):
        self.session_factory = get_session_factory()

    def save_run(self, run: TrainingRunRecord) -> TrainingRunRecord:
        with self.session_factory() as session:
            orm_run = TrainingRunORM(
                id=run.id or str(uuid.uuid4()),
                user_id=run.user_id,
                target_name=run.target_name,
                learning_mode=run.learning_mode,
                validation_strategy=run.validation_strategy,
                fast_dev_mode=run.fast_dev_mode,
                status=run.status,
                duration_seconds=run.duration_seconds,
                champion_model_name=run.champion_model_name,
                champion_metrics=run.champion_metrics,
                created_at=run.start_time or datetime.utcnow()
            )
            session.add(orm_run)
            session.commit()
            return run

    def list_recent_runs(self, limit: int = 10) -> List[TrainingRunRecord]:
        with self.session_factory() as session:
            rows = session.query(TrainingRunORM).order_by(TrainingRunORM.created_at.desc()).limit(limit).all()
            results = []
            for r in rows:
                results.append(TrainingRunRecord(
                    id=r.id,
                    user_id=r.user_id or "",
                    target_name=r.target_name,
                    learning_mode=r.learning_mode,
                    validation_strategy=r.validation_strategy,
                    fast_dev_mode=r.fast_dev_mode,
                    status=r.status,
                    start_time=r.created_at,
                    duration_seconds=r.duration_seconds,
                    champion_model_name=r.champion_model_name,
                    champion_metrics=r.champion_metrics
                ))
            return results


class IPredictionRepository(ABC):
    @abstractmethod
    def log_prediction(self, record: PredictionRecord) -> None:
        pass


class SQLAlchemyPredictionRepository(IPredictionRepository):
    def __init__(self):
        self.session_factory = get_session_factory()

    def log_prediction(self, record: PredictionRecord) -> None:
        with self.session_factory() as session:
            orm_pred = PredictionLogORM(
                id=record.id or str(uuid.uuid4()),
                target_name=record.target_name,
                learning_mode=record.learning_mode,
                model_used=record.model_used,
                predicted_value=record.predicted_value,
                baseline_value=record.baseline_value,
                residual_value=record.residual_value,
                unit=record.unit,
                created_at=record.created_at or datetime.utcnow()
            )
            session.add(orm_pred)
            session.commit()


class IWatershedRepository(ABC):
    @abstractmethod
    def get_all(self) -> List[WatershedRecord]:
        pass

    @abstractmethod
    def get_by_id(self, watershed_id: str) -> Optional[WatershedRecord]:
        pass


class IModelRegistryRepository(ABC):
    @abstractmethod
    def register_model(self, model: TrainedModelRecord) -> TrainedModelRecord:
        pass

    @abstractmethod
    def get_champion_model(self, target_name: str) -> Optional[TrainedModelRecord]:
        pass


class IReportRepository(ABC):
    @abstractmethod
    def log_report(self, record: ReportRecord) -> None:
        pass
