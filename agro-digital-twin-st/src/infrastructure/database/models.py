"""
Relational Database Models (PostgreSQL Architecture) for AgroTwin-AI.
Defines schemas for:
- Users & 4 Roles: ADMIN, RESEARCHER, ANALYST, GUEST
- Watersheds & HRUs
- Datasets
- Training Runs & Trained Models
- Predictions & Experiment Results
- Reports
"""

from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any, Optional, List


class UserRole(str, Enum):
    ADMIN = "ADMIN"
    RESEARCHER = "RESEARCHER"
    ANALYST = "ANALYST"
    GUEST = "GUEST"


@dataclass
class UserRecord:
    id: str
    username: str
    email: str
    password_hash: str  # Prepared for bcrypt
    role: UserRole
    created_at: datetime = field(default_factory=datetime.utcnow)
    is_active: bool = True


@dataclass
class WatershedRecord:
    id: str
    name: str
    basin_name: str
    area_km2: float
    outlet_lat: float
    outlet_lon: float
    country: str = "USA"
    state: str = "Iowa"
    description: str = ""


@dataclass
class HRURecord:
    id: str
    watershed_id: str
    hru_number: int
    soil_type: str
    slope_pct: float
    land_use: str  # Maize, Sorghum, Pasture
    area_ha: float
    cn2: float
    ksat_mm_h: float


@dataclass
class DatasetMetadataRecord:
    id: str
    name: str
    version: str
    file_path: str
    num_records: int
    is_synthetic: bool
    provenance_source: str
    created_at: datetime = field(default_factory=datetime.utcnow)
    checksum_sha256: Optional[str] = None


@dataclass
class TrainingRunRecord:
    id: str
    user_id: str
    target_name: str
    learning_mode: str  # direct or residual
    validation_strategy: str
    fast_dev_mode: bool
    status: str  # RUNNING, COMPLETED, FAILED
    start_time: datetime
    end_time: Optional[datetime] = None
    duration_seconds: Optional[float] = None
    champion_model_name: Optional[str] = None
    champion_metrics: Optional[Dict[str, float]] = None


@dataclass
class TrainedModelRecord:
    id: str
    training_run_id: str
    model_name: str
    model_type: str  # traditional, hybrid_deep
    artifact_path: str
    metrics: Dict[str, float]
    is_champion: bool = False
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class PredictionRecord:
    id: str
    model_id: str
    user_id: Optional[str]
    input_payload: Dict[str, Any]
    output_value: float
    predicted_residual: Optional[float]
    mode: str
    latency_ms: float
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class ExperimentResultRecord:
    id: str
    experiment_name: str
    hypothesis_h0: str
    hypothesis_h1: str
    wilcoxon_p_value: float
    bootstrap_ci_lower: float
    bootstrap_ci_upper: float
    rmse_reduction_pct: float
    verdict: str
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class ReportRecord:
    id: str
    user_id: str
    title: str
    file_format: str  # PDF, Word, Excel
    file_path: str
    created_at: datetime = field(default_factory=datetime.utcnow)
    data_provenance: str = "DEMO / SYNTHETIC DATA"
