from typing import List, Optional
from sqlalchemy import String, Float, Integer, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.app.core.database import Base
from backend.app.models.base import TimestampMixin

class ClimateScenario(Base, TimestampMixin):
    __tablename__ = "climate_scenarios"

    code: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    pathway: Mapped[str] = mapped_column(String(50), nullable=False) # e.g. "CMIP6 / SSP2-4.5"
    description: Mapped[str] = mapped_column(String(255), nullable=False)
    temp_anomaly_c: Mapped[float] = mapped_column(Float, default=0.0) # Incremento medio proyectado en °C
    precip_factor: Mapped[float] = mapped_column(Float, default=1.0) # Factor multiplicador (1.0 = 100%, 0.85 = -15%)
    co2_ppm: Mapped[float] = mapped_column(Float, default=415.0)

class SimulationRun(Base, TimestampMixin):
    __tablename__ = "simulation_runs"

    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    watershed_id: Mapped[str] = mapped_column(String(36), ForeignKey("watersheds.id", ondelete="CASCADE"), nullable=False)
    scenario_id: Mapped[str] = mapped_column(String(36), ForeignKey("climate_scenarios.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="COMPLETED") # "PENDING", "RUNNING", "COMPLETED", "FAILED"
    duration_days: Mapped[int] = mapped_column(Integer, default=365) # Simulación típica anual o plurianual
    irrigation_efficiency: Mapped[float] = mapped_column(Float, default=0.85) # Eficiencia de riego (goteo/aspersión)
    parameters: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    summary_metrics: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

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
    
    # Componentes Hidrológicos SWAT
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

    simulation_run: Mapped[SimulationRun] = relationship("SimulationRun", back_populates="results")
