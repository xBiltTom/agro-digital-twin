"""
Database models and repository contracts for PostgreSQL persistence.
"""

from .models import (
    UserRole,
    UserRecord,
    WatershedRecord,
    HRURecord,
    DatasetMetadataRecord,
    TrainingRunRecord,
    TrainedModelRecord,
    PredictionRecord,
    ExperimentResultRecord,
    ReportRecord
)
from .repositories import (
    IUserRepository,
    IWatershedRepository,
    ITrainingRunRepository,
    IModelRegistryRepository,
    IPredictionRepository,
    IReportRepository
)

__all__ = [
    "UserRole",
    "UserRecord",
    "WatershedRecord",
    "HRURecord",
    "DatasetMetadataRecord",
    "TrainingRunRecord",
    "TrainedModelRecord",
    "PredictionRecord",
    "ExperimentResultRecord",
    "ReportRecord",
    "IUserRepository",
    "IWatershedRepository",
    "ITrainingRunRepository",
    "IModelRegistryRepository",
    "IPredictionRepository",
    "IReportRepository"
]
