from typing import List, Optional, Any
from sqlalchemy import String, Float, Integer, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
from app.models.base import TimestampMixin

class PlantSpecies(Base, TimestampMixin):
    __tablename__ = "plant_species"

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    scientific_name: Mapped[str] = mapped_column(String(150), nullable=False)
    crop_type: Mapped[str] = mapped_column(String(50), default="Arbóreo / Frutal") # Cultivo arbóreo, gramínea, etc.
    base_kc: Mapped[float] = mapped_column(Float, default=1.05) # Coeficiente de cultivo Kc
    max_root_depth_cm: Mapped[float] = mapped_column(Float, default=120.0) # Profundidad radicular máxima
    optimal_temp_c: Mapped[float] = mapped_column(Float, default=24.0)
    stomatal_conductance_max: Mapped[float] = mapped_column(Float, default=300.0) # mmol/(m²·s)

class Watershed(Base, TimestampMixin):
    __tablename__ = "watersheds"

    code: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    country: Mapped[str] = mapped_column(String(100), default="Perú")
    area_km2: Mapped[float] = mapped_column(Float, nullable=False)
    elevation_min_m: Mapped[float] = mapped_column(Float, default=500.0)
    elevation_max_m: Mapped[float] = mapped_column(Float, default=4200.0)
    outlet_lat: Mapped[float] = mapped_column(Float, nullable=False)
    outlet_lon: Mapped[float] = mapped_column(Float, nullable=False)
    # Metadatos del DEM 3D para la visualización del terreno
    dem_metadata: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    subbasins: Mapped[List["Subbasin"]] = relationship(
        "Subbasin",
        back_populates="watershed",
        cascade="all, delete-orphan",
        lazy="selectin"
    )

class Subbasin(Base, TimestampMixin):
    __tablename__ = "subbasins"

    watershed_id: Mapped[str] = mapped_column(String(36), ForeignKey("watersheds.id", ondelete="CASCADE"), nullable=False)
    subbasin_number: Mapped[int] = mapped_column(Integer, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    area_km2: Mapped[float] = mapped_column(Float, nullable=False)
    mean_slope_percent: Mapped[float] = mapped_column(Float, default=12.5)
    reach_length_km: Mapped[float] = mapped_column(Float, default=15.2)

    watershed: Mapped[Watershed] = relationship("Watershed", back_populates="subbasins")
    hrus: Mapped[List["HRU"]] = relationship(
        "HRU",
        back_populates="subbasin",
        cascade="all, delete-orphan",
        lazy="selectin"
    )

class HRU(Base, TimestampMixin):
    """Unidad de Respuesta Hidrológica (Hydrological Response Unit de SWAT)."""
    __tablename__ = "hrus"

    subbasin_id: Mapped[str] = mapped_column(String(36), ForeignKey("subbasins.id", ondelete="CASCADE"), nullable=False)
    hru_number: Mapped[int] = mapped_column(Integer, nullable=False)
    land_use: Mapped[str] = mapped_column(String(50), nullable=False) # e.g. "AGRICULTURAL", "FOREST", "PASTURE"
    soil_type: Mapped[str] = mapped_column(String(50), nullable=False) # e.g. "FRANCO_ARCILLOSO"
    curve_number_ii: Mapped[float] = mapped_column(Float, default=74.0) # SCS Runoff Curve Number (Condición humedad media)
    area_fraction: Mapped[float] = mapped_column(Float, default=0.25)
    plant_species_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("plant_species.id"), nullable=True)

    subbasin: Mapped[Subbasin] = relationship("Subbasin", back_populates="hrus")
    plant_species: Mapped[Optional[PlantSpecies]] = relationship("PlantSpecies", lazy="selectin")
