"""
Feature Contract & Schema Definitions for AgroTwin-AI.
Enforces explicit contracts for model inputs and targets across 4 coupled scales:
  Level 1: Plant (FSPM)
  Level 2: Field
  Level 3: Watershed (SWAT+)
  Level 4: Climate & Management
"""

import json
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Any, Optional, Union
import pandas as pd
import numpy as np


@dataclass
class FeatureDefinition:
    """Explicit definition of a single model feature."""
    name: str
    dtype: str  # float, int, str
    unit: str
    scale_level: str  # Plant, Field, Watershed, Climate, Management
    min_val: Optional[float] = None
    max_val: Optional[float] = None
    required: bool = True
    default: Optional[Union[float, str]] = None
    description: str = ""

    def validate_value(self, val: Any) -> float:
        """Validates and converts a single feature value."""
        if val is None or (isinstance(val, float) and np.isnan(val)):
            if self.required and self.default is None:
                raise ValueError(f"Required feature '{self.name}' is missing with no default.")
            return float(self.default if self.default is not None else 0.0)

        num_val = float(val)
        if self.min_val is not None and num_val < self.min_val:
            # Clip or warn
            num_val = self.min_val
        if self.max_val is not None and num_val > self.max_val:
            num_val = self.max_val
        return num_val


FEATURE_GROUPS: Dict[str, List[FeatureDefinition]] = {
    "Climate": [
        FeatureDefinition("precip_mm", "float", "mm/month", "Climate", 0.0, 500.0, True, 60.0, "Monthly precipitation"),
        FeatureDefinition("temp_mean_c", "float", "°C", "Climate", -30.0, 45.0, True, 14.0, "Mean air temperature"),
        FeatureDefinition("solar_radiation", "float", "MJ/m2/day", "Climate", 0.0, 40.0, True, 18.0, "Mean solar radiation")
    ],
    "Soil_HRU": [
        FeatureDefinition("soil_moisture", "float", "% vol", "Watershed", 5.0, 50.0, True, 28.0, "Volumetric soil moisture content"),
        FeatureDefinition("infiltration_mm", "float", "mm/month", "Watershed", 0.0, 400.0, True, 45.0, "Soil infiltration depth")
    ],
    "Plant_FSPM": [
        FeatureDefinition("lai", "float", "m2/m2", "Plant", 0.0, 8.0, True, 2.5, "Leaf Area Index from FSPM"),
        FeatureDefinition("root_depth_m", "float", "m", "Plant", 0.05, 3.0, True, 0.8, "Effective rooting depth"),
        FeatureDefinition("transpiration_mm", "float", "mm/month", "Plant", 0.0, 250.0, True, 35.0, "Crop transpiration"),
        FeatureDefinition("water_stress", "float", "dimensionless", "Plant", 0.0, 1.0, True, 0.1, "Crop water stress index [0-1]")
    ],
    "Field": [
        FeatureDefinition("et_mm", "float", "mm/month", "Field", 0.0, 300.0, True, 50.0, "Aggregated evapotranspiration")
    ],
    "SWAT_Baseline": [
        FeatureDefinition("swat_baseline_runoff_mm", "float", "mm/month", "Watershed", 0.0, 300.0, False, 15.0, "SWAT+ uncoupled baseline runoff"),
        FeatureDefinition("swat_baseline_streamflow_m3s", "float", "m3/s", "Watershed", 0.0, 500.0, False, 8.0, "SWAT+ uncoupled baseline streamflow")
    ],
    "Yield_Seasonal": [
        FeatureDefinition("seasonal_precip_mm", "float", "mm/season", "Climate", 0.0, 2000.0, True, 450.0, "Total growing season precipitation"),
        FeatureDefinition("growing_season_temp_mean_c", "float", "°C", "Climate", 5.0, 38.0, True, 21.0, "Mean growing season temperature"),
        FeatureDefinition("gdd", "float", "GDD °C·d", "Climate", 0.0, 3500.0, True, 1600.0, "Growing degree days (base 10°C)"),
        FeatureDefinition("seasonal_et_mm", "float", "mm/season", "Field", 0.0, 1200.0, True, 480.0, "Total seasonal evapotranspiration"),
        FeatureDefinition("seasonal_transpiration_mm", "float", "mm/season", "Plant", 0.0, 1000.0, True, 320.0, "Total seasonal transpiration"),
        FeatureDefinition("mean_soil_moisture", "float", "% vol", "Watershed", 5.0, 50.0, True, 28.0, "Mean soil moisture in growing season"),
        FeatureDefinition("mean_water_stress", "float", "dimensionless", "Plant", 0.0, 1.0, True, 0.15, "Mean water stress index [0-1]"),
        FeatureDefinition("peak_lai", "float", "m2/m2", "Plant", 0.0, 8.0, True, 4.2, "Maximum peak leaf area index"),
        FeatureDefinition("max_root_depth_m", "float", "m", "Plant", 0.1, 3.0, True, 1.4, "Maximum rooting depth reached")
    ]
}


@dataclass
class TargetSchema:
    """Contract for a specific prediction target."""
    target_name: str
    unit: str
    description: str
    baseline_variable: Optional[str] = None
    target_type: str = "runoff"  # runoff, streamflow, yield

    def get_baseline_col(self) -> Optional[str]:
        return self.baseline_variable


TARGET_REGISTRY: Dict[str, TargetSchema] = {
    "monthly_runoff_mm": TargetSchema(
        target_name="monthly_runoff_mm",
        unit="mm/month",
        description="Coupled Monthly Watershed Runoff",
        baseline_variable="swat_baseline_runoff_mm",
        target_type="runoff"
    ),
    "monthly_streamflow_m3s": TargetSchema(
        target_name="monthly_streamflow_m3s",
        unit="m3/s",
        description="Coupled Monthly Streamflow at Watershed Outlet",
        baseline_variable="swat_baseline_streamflow_m3s",
        target_type="streamflow"
    ),
    "maize_yield_t_ha": TargetSchema(
        target_name="maize_yield_t_ha",
        unit="t/ha",
        description="Maize Grain Yield at Harvest",
        baseline_variable=None,
        target_type="yield"
    )
}


class ModelFeatureSchema:
    """
    Validates and manages the ordered list of feature definitions for a model bundle.
    Can be exported to and imported from JSON for cross-service sharing (FastAPI).
    """

    def __init__(self, features: List[FeatureDefinition]):
        self.features = features
        self.feature_names = [f.name for f in features]
        self._feature_map = {f.name: f for f in features}

    def validate_payload(self, payload: Dict[str, Any]) -> List[float]:
        """
        Validates an input dictionary and returns a strict ordered float list.
        """
        ordered_vals = []
        for feat in self.features:
            raw_val = payload.get(feat.name, feat.default)
            clean_val = feat.validate_value(raw_val)
            ordered_vals.append(clean_val)
        return ordered_vals

    def validate_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Validates that a DataFrame contains all required features in the correct order.
        """
        clean_df = pd.DataFrame(index=df.index)
        for feat in self.features:
            if feat.name not in df.columns:
                if feat.default is not None:
                    clean_df[feat.name] = feat.default
                else:
                    raise KeyError(f"Required feature '{feat.name}' missing from input DataFrame.")
            else:
                series = df[feat.name].copy()
                if feat.min_val is not None:
                    series = series.clip(lower=feat.min_val)
                if feat.max_val is not None:
                    series = series.clip(upper=feat.max_val)
                clean_df[feat.name] = series.fillna(feat.default if feat.default is not None else 0.0)
        return clean_df[self.feature_names]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "feature_names": self.feature_names,
            "features": [asdict(f) for f in self.features]
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ModelFeatureSchema":
        feats = []
        for f_data in data.get("features", []):
            feats.append(FeatureDefinition(**f_data))
        return cls(feats)

    @classmethod
    def from_json(cls, json_str: str) -> "ModelFeatureSchema":
        data = json.loads(json_str)
        return cls.from_dict(data)


def get_default_feature_schema(
    mode: str = "direct",
    include_baseline: bool = False,
    target_name: str = "monthly_runoff_mm"
) -> ModelFeatureSchema:
    """
    Builds the default feature schema for Maize Plant-to-Watershed modeling.
    If target_name == "maize_yield_t_ha", returns seasonal crop yield features.
    If mode is 'residual' or include_baseline is True, SWAT+ baseline variables are included.
    """
    if target_name == "maize_yield_t_ha":
        return ModelFeatureSchema(FEATURE_GROUPS["Yield_Seasonal"])

    selected_features: List[FeatureDefinition] = []
    for group in ["Climate", "Soil_HRU", "Plant_FSPM", "Field"]:
        selected_features.extend(FEATURE_GROUPS[group])

    if mode == "residual" or include_baseline:
        selected_features.extend(FEATURE_GROUPS["SWAT_Baseline"])

    return ModelFeatureSchema(selected_features)


def get_target_schema(target_name: str) -> TargetSchema:
    """Retrieves target schema definition by name."""
    if target_name not in TARGET_REGISTRY:
        raise KeyError(f"Unknown target '{target_name}'. Available: {list(TARGET_REGISTRY.keys())}")
    return TARGET_REGISTRY[target_name]
