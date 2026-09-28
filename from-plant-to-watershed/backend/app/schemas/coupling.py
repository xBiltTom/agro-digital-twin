"""Small, explicit contracts for FSPM values mapped into SWAT+ inputs."""

from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class CouplingLaiParameterContract(BaseModel):
    """Seasonal LAI-curve parameters; no dated field statistics are accepted."""

    model_config = ConfigDict(extra="forbid")

    lai_pot: float = Field(ge=0.5, le=10.0)
    frac_hu1: float = Field(gt=0.0, lt=1.0)
    lai_max1: float = Field(gt=0.0, lt=1.0)
    frac_hu2: float = Field(gt=0.0, lt=1.0)
    lai_max2: float = Field(gt=0.0, le=1.0)
    hu_lai_decl: float = Field(ge=0.2, le=1.0)
    season_count: int = Field(ge=1)
    derivation: str

    @model_validator(mode="after")
    def validate_curve_order(self):
        if not self.frac_hu1 < self.frac_hu2 < self.hu_lai_decl:
            raise ValueError("LAI heat-unit fractions must satisfy frac_hu1 < frac_hu2 < hu_lai_decl")
        if not self.lai_max1 < self.lai_max2:
            raise ValueError("LAI curve values must satisfy lai_max1 < lai_max2")
        return self


class CouplingPeakDates(BaseModel):
    model_config = ConfigDict(extra="forbid")

    date_of_peak_LAI: date
    date_of_peak_height: date
    date_of_peak_root_depth: date


class CouplingPlantParameterSummary(BaseModel):
    """Only the seasonal values consumed by ``SwatPlantParameterMapper``.

    Dated LAI/root distributions, stress, ET, biomass, moisture, and phenology
    belong to individual playback records and are intentionally not fields here.
    """

    model_config = ConfigDict(extra="forbid")

    summary_semantics: Literal["SEASONAL_MAXIMA_FOR_COUPLING_NOT_A_DATED_FSPM_STATE"]
    swat_lai_contract: CouplingLaiParameterContract
    plant_height_mean_m: float = Field(ge=0.0)
    root_depth_mean_m: float = Field(ge=0.0)
    canopy_extinction_coefficient: float = Field(ge=0.0, le=2.0)
    biomass_energy_ratio_kg_ha_per_mj_m2: float = Field(ge=10.0, le=90.0)
    peak_dates: CouplingPeakDates
    coupling_parameter_provenance: dict[str, dict]
