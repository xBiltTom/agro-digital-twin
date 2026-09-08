from typing import List, Optional
from datetime import datetime
from sqlalchemy import String, Float, Integer, ForeignKey, JSON, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
from app.models.base import TimestampMixin

class ClimateScenario(Base, TimestampMixin):
    __tablename__ = "climate_scenarios"

    code: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    pathway: Mapped[str] = mapped_column(String(50), nullable=False) # e.g. "CMIP6 / SSP2-4.5"
    description: Mapped[str] = mapped_column(String(255), nullable=False)
    temp_anomaly_c: Mapped[float] = mapped_column(Float, default=0.0) # Incremento medio proyectado en °C
    precip_factor: Mapped[float] = mapped_column(Float, default=1.0) # Factor multiplicador (1.0 = 100%, 0.85 = -15%)
    co2_ppm: Mapped[float] = mapped_column(Float, default=415.0)
    source_type: Mapped[str] = mapped_column(String(30), default="SYNTHETIC", nullable=False)

class SimulationRun(Base, TimestampMixin):
    __tablename__ = "simulation_runs"

    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    watershed_id: Mapped[str] = mapped_column(String(36), ForeignKey("watersheds.id", ondelete="CASCADE"), nullable=False)
    scenario_id: Mapped[str] = mapped_column(String(36), ForeignKey("climate_scenarios.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="PENDING")
    duration_days: Mapped[int] = mapped_column(Integer, default=365) # Simulación típica anual o plurianual
    irrigation_efficiency: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # legacy, unsupported
    parameters: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    summary_metrics: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    seed: Mapped[int] = mapped_column(Integer, default=42, nullable=False)
    requested_config: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    effective_config: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    provenance: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    error: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    mode: Mapped[str] = mapped_column(String(40), default="DEMO_MULTISCALE", nullable=False)
    plant_count: Mapped[int] = mapped_column(Integer, default=1000, nullable=False)
    hydrology_backend: Mapped[str] = mapped_column(String(40), default="SIMPLIFIED", nullable=False)
    external_model_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    field_aggregates: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    hru_aggregates: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    plant_sample: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    monthly_outputs: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    validation: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    ml_result: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    management_scenario: Mapped[str] = mapped_column(String(40), default="BASELINE", nullable=False)
    climate_source: Mapped[str] = mapped_column(String(40), default="SYNTHETIC", nullable=False)
    dataset_ids: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)

    scenario: Mapped[ClimateScenario] = relationship("ClimateScenario", lazy="selectin")
    results: Mapped[List["SimulationResult"]] = relationship(
        "SimulationResult",
        back_populates="simulation_run",
        cascade="all, delete-orphan",
        order_by="SimulationResult.day_index",
        lazy="select"
    )

class SimulationResult(Base, TimestampMixin):
    __tablename__ = "simulation_results"

    simulation_run_id: Mapped[str] = mapped_column(String(36), ForeignKey("simulation_runs.id", ondelete="CASCADE"), index=True, nullable=False)
    day_index: Mapped[int] = mapped_column(Integer, nullable=False)
    date_str: Mapped[str] = mapped_column(String(20), nullable=False)
    
    # Forzamiento climático
    precip_mm: Mapped[float] = mapped_column(Float, nullable=False)
    temp_c: Mapped[float] = mapped_column(Float, nullable=False)
    solar_rad_mj: Mapped[float] = mapped_column(Float, default=18.5)
    
    # Componentes del modelo hidrológico simplificado
    potential_et_mm: Mapped[float] = mapped_column(Float, nullable=False)
    actual_et_mm: Mapped[float] = mapped_column(Float, nullable=False)
    surface_runoff_mm: Mapped[float] = mapped_column(Float, nullable=False)
    percolation_mm: Mapped[float] = mapped_column(Float, nullable=False)
    streamflow_m3s: Mapped[float] = mapped_column(Float, nullable=False)
    
    # Estado del Suelo (Meso)
    soil_moisture_vol: Mapped[float] = mapped_column(Float, nullable=False) # % volumétrico (0 - 45%)
    soil_water_depth_mm: Mapped[float] = mapped_column(Float, default=180.0)
    
    # Fisiología de la Planta (Micro)
    plant_transpiration_mm: Mapped[float] = mapped_column(Float, nullable=False)
    root_water_uptake_mm: Mapped[float] = mapped_column(Float, nullable=False) # Feddes RWU
    cwsi_stress_index: Mapped[float] = mapped_column(Float, default=0.15) # 0.0 (Sin estrés) a 1.0 (Estrés severo)
    sap_flow_velocity_cmh: Mapped[float] = mapped_column(Float, default=12.4) # Flujo de savia en cm/h
    water_balance_residual_mm: Mapped[float] = mapped_column(Float, default=0.0)

    simulation_run: Mapped[SimulationRun] = relationship("SimulationRun", back_populates="results")
