"""Run the existing simplified FSPM on SWAT+ executed HRU crop calendars."""

from __future__ import annotations

from collections import Counter
from copy import deepcopy
from dataclasses import dataclass, replace
from datetime import date, timedelta
from pathlib import Path
from typing import Any

from scientific_core import PlantPopulation, PlantToFieldAggregator
from scientific_core.units import ASSUMED_FSPM_SOIL_MOISTURE_VOL_PERCENT

from app.services.swat_executed_calendar import CropCalendarGroup, SwatExecutedCropCalendar
from app.services.swat_plant_parameter_mapper import SwatClimateForcingReader
from app.services.swat_soil_water import hru_water_state, read_hru_soils


@dataclass(frozen=True)
class ExecutedCalendarFspmRun:
    fspm_days: dict[str, dict[str, Any]]
    dated_fields: list[tuple[str, dict[str, Any]]]
    seasonal_contracts: list[dict[str, Any]]
    seasonal_weights: list[float]
    trait_dated_fields: list[tuple[str, dict[str, Any]]]
    field_climate: list[dict[str, Any]]
    group_daily: list[dict[str, Any]]
    provenance: dict[str, Any]


def _calendar_signature(calendar: SwatExecutedCropCalendar) -> dict[int, tuple[str, str]]:
    return {
        hru_id: (group.planting_date, group.harvest_date)
        for group in calendar.groups for hru_id in group.hru_ids
    }


def _combine_daily_fields(
    groups: tuple[CropCalendarGroup, ...],
    active_rows: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    total_weight = sum(group.spatial_weight for group in groups)
    active_groups = [group for group in groups if group.calendar_id in active_rows]
    active_weight = sum(group.spatial_weight for group in active_groups)
    if total_weight <= 0 or active_weight <= 0:
        raise ValueError("executed-calendar FSPM aggregate has no positive spatial weight")

    structural = {
        "mean_lai", "mean_LAI", "canopy_cover",
    }
    active_only = {
        "plant_height_mean_m", "root_depth_mean_m", "biomass_g_plant",
        "mean_growing_degree_days_c_day", "phenology_fraction",
        "mean_thermal_maturity_gdd", "canopy_extinction_coefficient",
        "biomass_energy_ratio_kg_ha_per_mj_m2",
        "mean_transpiration_mm", "mean_stress", "actual_ET_mm_day", "potential_ET_mm_day",
        "transpiration_mm_day", "soil_water_uptake_mm_day", "yield_estimate_g_plant",
        "soil_moisture_vol",
        "estimated_plant_available_fraction", "estimated_root_zone_depth_mm",
        "wilting_point_vol_percent", "field_capacity_vol_percent",
    }
    sample = next(iter(active_rows.values()))["field"]
    result: dict[str, Any] = {
        key: deepcopy(value) for key, value in sample.items()
        if key in {"units", "evidence_type", "provenance", "coupling_parameter_provenance"}
    }
    numeric_keys = {
        key for row in active_rows.values() for key, value in row["field"].items()
        if isinstance(value, (int, float)) and not isinstance(value, bool)
    }
    for key in numeric_keys & (structural | active_only):
        denominator = total_weight if key in structural else active_weight
        weighted = 0.0
        for group in groups:
            row = active_rows.get(group.calendar_id)
            value = float(row["field"].get(key, 0.0)) if row is not None else 0.0
            weighted += group.spatial_weight * value
        result[key] = weighted / denominator
    result["n_plants"] = sum(int(active_rows[group.calendar_id]["field"]["n_plants"]) for group in active_groups)
    result["active_crop_area_fraction"] = active_weight / total_weight
    result["active_calendar_group_count"] = len(active_groups)
    result["calendar_group_count"] = len(groups)
    result["soil_moisture_source"] = sample.get("soil_moisture_source", "ASSUMED_CONSTANT_NOT_SWAT_OUTPUT")
    result["calendar_aggregation"] = "SWAT_HRU_AREA_X_2019_CDL_CORN_FRACTION_WEIGHTED; inactive calendar groups contribute zero living-crop structure"
    result["summary_semantics"] = "DATED_FSPM_MAIZE_AREA_STATE_ACROSS_EXECUTED_SWAT_CALENDARS"
    return result


def run_fspm_on_executed_calendar(
    *,
    project: str | Path,
    calendar: SwatExecutedCropCalendar,
    start_date: date,
    end_date: date,
    plant_count: int,
    seed: int,
    crop_fraction_by_hru: dict[int, float] | None = None,
    crop: str = "maize",
    hru_water_results: list[dict[str, Any]] | None = None,
) -> ExecutedCalendarFspmRun:
    """Create dated group and field FSPM states using the assigned SWAT weather."""
    root = Path(project)
    if (root / "TxtInOut" / "file.cio").is_file():
        root = root / "TxtInOut"
    reader = SwatClimateForcingReader(root)
    target_hrus = sorted(calendar.hru_calendar)
    field_climate, field_climate_provenance = reader.for_hrus(
        start_date, end_date, target_hrus,
        crop_fraction_by_hru=crop_fraction_by_hru,
    )
    header_rows = (root / "plants.plt").read_text(encoding="utf-8", errors="strict").splitlines()
    if len(header_rows) < 3:
        raise ValueError("plants.plt is too short to read FSPM growth-temperature base")
    headers = header_rows[1].split()
    plant_record = next((line.split() for line in header_rows[2:] if line.split() and line.split()[0] == "corn"), None)
    if plant_record is None or "tmp_base" not in headers:
        raise ValueError("plants.plt does not expose corn.tmp_base for the FSPM growth clock")
    growth_base_c = float(plant_record[headers.index("tmp_base")])
    soil_profiles = read_hru_soils(root) if hru_water_results is not None else {}
    water_by_hru_day: dict[tuple[int, str], float] = {}
    if hru_water_results is not None:
        for row in hru_water_results:
            key = int(row["hru_unit"]), str(row["period"])
            if key in water_by_hru_day:
                raise ValueError(f"Duplicate SWAT+ HRU soil-water row {key}")
            water_by_hru_day[key] = float(row["soil_water_average_mm"])
        missing = [(hru, (start_date + timedelta(days=index)).isoformat())
                   for hru in target_hrus for index in range((end_date - start_date).days + 1)
                   if (hru, (start_date + timedelta(days=index)).isoformat()) not in water_by_hru_day]
        if missing:
            raise ValueError(f"Missing daily SWAT+ HRU soil-water storage: {missing[:3]}")
        hru_weights = SwatExecutedCropCalendar.hru_spatial_weights(root, crop_fraction_by_hru)
    else:
        hru_weights = {}

    group_rows: dict[str, dict[str, dict[str, Any]]] = {}
    group_climate_provenance: dict[str, Any] = {}
    group_contracts: list[dict[str, Any]] = []
    group_contract_weights: list[float] = []
    trait_dated_fields: list[tuple[str, dict[str, Any]]] = []
    group_daily: list[dict[str, Any]] = []
    day_count = (end_date - start_date).days + 1
    for group in calendar.groups:
        group_forcing, forcing_provenance = reader.for_hrus(
            start_date, end_date, list(group.hru_ids),
            crop_fraction_by_hru=crop_fraction_by_hru,
        )
        forcing_by_date = {row["date"]: row for row in group_forcing}
        if len(forcing_by_date) != day_count:
            raise ValueError(f"calendar group {group.calendar_id} does not have complete dated forcing")
        population = PlantPopulation(count=plant_count, seed=seed, crop=crop)
        plant_date, harvest_date = date.fromisoformat(group.planting_date), date.fromisoformat(group.harvest_date)
        if plant_date < start_date or harvest_date > end_date:
            raise ValueError(f"calendar group {group.calendar_id} falls outside the requested FSPM interval")
        cursor = plant_date
        gdd = absorbed_par = 0.0
        root_depth_m = .08
        rows_by_date: dict[str, dict[str, Any]] = {}
        while cursor <= harvest_date:
            day = cursor.isoformat()
            weather = forcing_by_date[day]
            gdd += max(0.0, float(weather["temp_c"]) - growth_base_c)
            daily_forcing = {
                "temp_c": weather["temp_c"], "solar_rad_mj": weather["solar_rad_mj"],
                "rh_percent": weather["rh_percent"], "co2_ppm": weather["co2_ppm"],
                "gdd_c_day": gdd, "cumulative_absorbed_par_mj_m2": absorbed_par,
            }
            hru_water = {}
            if hru_water_results is not None:
                for hru in group.hru_ids:
                    hru_water[hru] = hru_water_state(
                        soil_profiles[hru], water_by_hru_day[hru, day], root_depth_m)
                denominator = sum(hru_weights[hru] for hru in group.hru_ids)
                def weighted(name: str) -> float:
                    return sum(hru_weights[hru] * float(hru_water[hru][name])
                               for hru in group.hru_ids) / denominator
                moisture = weighted("estimated_soil_moisture_vol_percent")
                thresholds = tuple(weighted(name) for name in (
                    "wilting_point_vol_percent", "field_capacity_vol_percent", "saturation_vol_percent"))
                source = "DERIVED_SWAT_PROFILE_UNIFORM_ROOT_ZONE_APPROXIMATION"
            else:
                moisture, thresholds = ASSUMED_FSPM_SOIL_MOISTURE_VOL_PERCENT, None
                source = "ASSUMED_CONSTANT_NOT_SWAT_OUTPUT"
            plants = population.step((cursor - start_date).days + 1, daily_forcing,
                                     soil_moisture_vol=moisture, soil_thresholds=thresholds)
            field = PlantToFieldAggregator.aggregate(plants, moisture)
            field["soil_moisture_source"] = source
            if hru_water:
                field["estimated_plant_available_fraction"] = weighted("estimated_plant_available_fraction")
                field["estimated_root_zone_depth_mm"] = weighted("estimated_root_zone_depth_mm")
                field["wilting_point_vol_percent"] = thresholds[0]
                field["field_capacity_vol_percent"] = thresholds[1]
            root_depth_m = float(field["root_depth_mean_m"])
            field["calendar_id"] = group.calendar_id
            field["calendar_hru_ids"] = list(group.hru_ids)
            field["calendar_spatial_weight"] = group.spatial_weight
            field["phenological_stage"] = Counter(state.phenological_stage for state in plants).most_common(1)[0][0]
            sampled = population.representative_sample(plants)
            row = {
                "date": day,
                "calendar_id": group.calendar_id,
                "planting_date": group.planting_date,
                "harvest_date": group.harvest_date,
                "hru_ids": list(group.hru_ids),
                "spatial_weight": group.spatial_weight,
                "field": deepcopy(field),
                "plants": sampled,
                "plant_sample_context": {
                    "population_count": len(plants), "captured_count": len(sampled),
                    "selection_method": "EVENLY_SPACED_STABLE_IDS" if len(plants) > 10 else "ALL_REPRESENTATIVE_STATES",
                    "identity_scope": "SIMULATION_SLOT",
                    "identity_semantics": f"Modeled representative plants for management-calendar group {group.calendar_id}; not observed plant individuals",
                },
                "forcing": weather,
                "hru_water": hru_water,
            }
            rows_by_date[day] = row
            group_daily.append(row)
            trait_dated_fields.append((day, deepcopy(field)))
            absorbed_par += max(0.0, float(weather["solar_rad_mj"])) * .48 * field["canopy_cover"]
            cursor += timedelta(days=1)
        group_rows[group.calendar_id] = rows_by_date
        group_climate_provenance[group.calendar_id] = forcing_provenance
        if len(rows_by_date) >= 3:
            group_contracts.append(PlantToFieldAggregator.seasonal_lai_contract(
                row["field"] for row in rows_by_date.values()
            ))
            group_contract_weights.append(group.spatial_weight)
    if not group_contracts:
        raise ValueError("No executed crop calendar produced a usable FSPM seasonal LAI contract")

    fspm_days: dict[str, dict[str, Any]] = {}
    dated_fields: list[tuple[str, dict[str, Any]]] = []
    cursor = start_date
    while cursor <= end_date:
        day = cursor.isoformat()
        active_rows = {group.calendar_id: group_rows[group.calendar_id][day]
                       for group in calendar.groups if day in group_rows[group.calendar_id]}
        if active_rows:
            field = _combine_daily_fields(calendar.groups, active_rows)
            group_summaries = []
            plant_samples = []
            stage_weights: dict[str, float] = {}
            for group in calendar.groups:
                row = active_rows.get(group.calendar_id)
                if row is None:
                    continue
                group_summaries.append({
                    "calendar_id": group.calendar_id, "hru_ids": list(group.hru_ids),
                    "planting_date": group.planting_date, "harvest_date": group.harvest_date,
                    "spatial_weight": group.spatial_weight,
                    "active": True, "field": row["field"],
                })
                stage = row["field"]["phenological_stage"]
                stage_weights[stage] = stage_weights.get(stage, 0.0) + group.spatial_weight
                plant_samples.extend(replace(plant, plant_id=f"{group.calendar_id}:{plant.plant_id}")
                                     for plant in row["plants"])
            dominant_stage = max(stage_weights, key=stage_weights.get)
            sample_context = {
                "population_count": plant_count * len(active_rows),
                "captured_count": len(plant_samples),
                "selection_method": "EVENLY_SPACED_STABLE_IDS" if plant_count > 10 else "ALL_REPRESENTATIVE_STATES",
                "identity_scope": "SIMULATION_SLOT",
                "identity_semantics": "Samples retain their SWAT-executed management-calendar group in plant_id; they are modeled slots, not observed individual plants",
            }
            calendar_ids = sorted(active_rows)
            fspm_days[day] = {
                "crop": {
                    "active": True, "crop": "maize",
                    "season_id": calendar_ids[0] if len(calendar_ids) == 1 else "MULTIPLE_EXECUTED_SWAT_HRU_CALENDARS",
                    "phenological_stage": dominant_stage,
                    "window_status": "EXECUTED_SWAT_MANAGEMENT_EVENTS",
                    "source": "SWAT+ mgt_out.txt PLANT and HARV/KILL events by HRU",
                    "limitation": "FSPM grows each distinct HRU calendar separately; field playback is weighted over the mapped maize HRU area. Daily event timing is applied to the complete day.",
                },
                "field": field,
                "plants": plant_samples,
                "plant_sample_context": sample_context,
                "calendar_groups": group_summaries,
                "hru_water": {str(hru): water for row in active_rows.values()
                              for hru, water in row["hru_water"].items()},
            }
            dated_fields.append((day, deepcopy(field)))
        else:
            fspm_days[day] = {
                "crop": {"active": False, "source": "SWAT+ mgt_out.txt executed crop calendar",
                         "window_status": "NO_ACTIVE_EXECUTED_CROP_CALENDAR",
                         "limitation": "No maize cohort is within its executed SWAT+ plant-to-harvest interval; no plant state is emitted"}
            }
        cursor += timedelta(days=1)
    if not dated_fields:
        raise ValueError("Executed SWAT+ calendars did not produce dated FSPM states")

    return ExecutedCalendarFspmRun(
        fspm_days=fspm_days,
        dated_fields=dated_fields,
        seasonal_contracts=group_contracts,
        seasonal_weights=group_contract_weights,
        trait_dated_fields=trait_dated_fields,
        field_climate=field_climate,
        group_daily=group_daily,
        provenance={
            "calendar": calendar.as_dict(),
            "growth_temperature_base_c": growth_base_c,
            "growth_temperature_base_source": "plants.plt.corn.tmp_base",
            "climate_source": "SWAT+ weather-sta.cli assigned station files, selected by hru.con.wst",
            "field_climate": field_climate_provenance,
            "calendar_group_climate": group_climate_provenance,
            "soil_moisture": {
                "source": "SWAT+ hru_wb_day.sw_ave + hru-data.hru.soil + soils.sol" if hru_water_results is not None else "ASSUMED_CONSTANT_NOT_SWAT_OUTPUT",
                "classification": "DERIVED" if hru_water_results is not None else "ASSUMED",
                "unit": "volumetric percent",
                "method": "SWAT+ daily average storage excludes wilting-point water. Divide it by soils.sol profile field-capacity storage above wilting point, then apply that available-water fraction to each layer intersecting the FSPM root zone and add layer-specific wilting-point water. Calendar-group values are HRU crop-area weighted." if hru_water_results is not None else "constant 24 vol%",
                "limitation": "SWAT+ daily output lacks layer water states; the root-zone estimate assumes a uniform available-water fraction across layers, not measured layer moisture. FSPM groups average distinct HRU soils and storage." if hru_water_results is not None else "SWAT+ storage is not connected.",
            },
            "thermal_maturity_gdd": {
                "value": PlantPopulation(seed=seed, count=1).thermal_maturity_gdd,
                "classification": "ASSUMED_SIMPLIFIED_FSPM_REFERENCE",
                "limitation": "SWAT+ days_mat is in days and does not determine the FSPM thermal-maturity value.",
            },
            "calendar_aggregation": "one FSPM population per unique executed planting/harvest pair; crop-area-weighted field states",
        },
    )
