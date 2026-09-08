from typing import Any

from .provenance import EvidenceType, Provenance


class SimplifiedHydrologyModel:
    """Daily SCS-CN/two-store conceptual model. It does not execute SWAT+."""

    VERSION = "1.0"

    def __init__(self, watershed_area_km2: float = 420.5, curve_number: float = 74.0,
                 soil_profile_depth_mm: float = 1000.0, initial_soil_moisture_vol: float = 24.0,
                 initial_groundwater_storage_mm: float = 65.0):
        if watershed_area_km2 <= 0 or soil_profile_depth_mm <= 0 or not 30 <= curve_number <= 98:
            raise ValueError("invalid hydrology model configuration")
        if not 0 <= initial_soil_moisture_vol <= 44 or initial_groundwater_storage_mm < 0:
            raise ValueError("initial storages are outside the supported domain")
        self.area_km2, self.curve_number, self.profile_depth_mm = watershed_area_km2, curve_number, soil_profile_depth_mm
        self.theta_sat, self.theta_fc, self.theta_wp = 44.0, 32.0, 12.0
        self.fc_depth_mm, self.sat_depth_mm = soil_profile_depth_mm * .32, soil_profile_depth_mm * .44
        self.soil_water_mm = soil_profile_depth_mm * initial_soil_moisture_vol / 100.0
        self.groundwater_storage_mm = initial_groundwater_storage_mm
        self.cumulative_balance_residual_mm = 0.0

    @property
    def provenance(self) -> Provenance:
        return Provenance(self.__class__.__name__, self.VERSION, EvidenceType.SIMPLIFIED,
                          "lumped watershed", "daily",
                          {"precipitation": "mm/day", "irrigation": "mm/day", "runoff": "mm/day", "storage": "mm", "streamflow": "m3/s"})

    def calculate_scs_runoff(self, precip_mm: float, soil_moisture_vol: float) -> float:
        if precip_mm < 0:
            raise ValueError("precip_mm cannot be negative")
        if precip_mm == 0:
            return 0.0
        cn = self.curve_number
        if soil_moisture_vol > self.theta_fc:
            cn = cn / (0.4036 + 0.0059 * cn)
        elif soil_moisture_vol < self.theta_wp * 1.3:
            cn = (4.2 * cn) / (10.0 - 0.058 * cn)
        cn = max(35.0, min(98.0, cn))
        retention = 25400.0 / cn - 254.0
        abstraction = .2 * retention
        if precip_mm <= abstraction:
            return 0.0
        return min(precip_mm, (precip_mm - abstraction) ** 2 / (precip_mm - abstraction + retention))

    def calculate_daily_step(self, precip_mm: float, plant_transpiration_mm: float,
                             potential_et_mm: float, irrigation_mm: float = 0.0,
                             root_depth_cm: float | None = None) -> dict[str, Any]:
        if min(precip_mm, plant_transpiration_mm, potential_et_mm, irrigation_mm) < 0:
            raise ValueError("water fluxes cannot be negative")
        soil_before, gw_before = self.soil_water_mm, self.groundwater_storage_mm
        previous_theta = soil_before / self.profile_depth_mm * 100.0
        runoff = self.calculate_scs_runoff(precip_mm, previous_theta)
        self.soil_water_mm += precip_mm - runoff + irrigation_mm
        soil_evaporation = max(0.0, potential_et_mm - plant_transpiration_mm) * .35 * min(1.0, previous_theta / self.theta_fc)
        root_access_fraction = 1.0 if root_depth_cm is None else max(0.10, min(1.0, root_depth_cm / (self.profile_depth_mm / 10.0)))
        actual_et = min(self.soil_water_mm * root_access_fraction, plant_transpiration_mm + soil_evaporation)
        self.soil_water_mm -= actual_et
        percolation = max(0.0, self.soil_water_mm - self.fc_depth_mm) * .45
        self.soil_water_mm -= percolation
        self.groundwater_storage_mm += percolation
        if self.soil_water_mm > self.sat_depth_mm:
            runoff += self.soil_water_mm - self.sat_depth_mm
            self.soil_water_mm = self.sat_depth_mm
        baseflow = min(self.groundwater_storage_mm, self.groundwater_storage_mm * .045)
        self.groundwater_storage_mm -= baseflow
        storage_change = (self.soil_water_mm + self.groundwater_storage_mm) - (soil_before + gw_before)
        residual = precip_mm + irrigation_mm - runoff - actual_et - baseflow - storage_change
        self.cumulative_balance_residual_mm += residual
        total_runoff = runoff + baseflow
        return {"surface_runoff_mm": runoff, "actual_et_mm": actual_et, "soil_evaporation_mm": soil_evaporation,
                "percolation_mm": percolation, "baseflow_mm": baseflow,
                "soil_water_depth_mm": self.soil_water_mm,
                "groundwater_storage_mm": self.groundwater_storage_mm,
                "soil_moisture_vol": self.soil_water_mm / self.profile_depth_mm * 100.0,
                "streamflow_m3s": total_runoff * self.area_km2 * 1000.0 / 86400.0,
                "root_access_fraction": root_access_fraction, "water_balance_residual_mm": residual,
                "cumulative_water_balance_residual_mm": self.cumulative_balance_residual_mm}
