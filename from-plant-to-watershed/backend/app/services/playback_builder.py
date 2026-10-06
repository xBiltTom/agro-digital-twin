"""Compose dated FSPM, forcing and hydrology without inventing missing states."""

from __future__ import annotations

from collections import defaultdict
from calendar import isleap, monthrange
from datetime import date, timedelta
from statistics import fmean
from typing import Any, Iterable

from app.schemas.playback import ChannelState, CropState, Evidence, HruState, PlaybackRecord, PlantSample, VariableState
from app.services.swat_soil_water import SoilProfile, hru_water_state


def value(number: float | str | None, unit: str, evidence: Evidence, source: str,
          limitation: str | None = None) -> VariableState:
    if number is None:
        return VariableState(value=None, unit=unit, evidence=Evidence.NOT_AVAILABLE,
                             source=source, availability="NOT_AVAILABLE", limitation=limitation or "No recorded value")
    return VariableState(value=number, unit=unit, evidence=evidence, source=source,
                         availability="AVAILABLE", limitation=limitation)


def _weather(row: dict | None, *, resolution: str, source: str,
             evidence: Evidence) -> dict[str, VariableState]:
    row = row or {}
    flux_unit = "mm/day" if resolution == "DAILY" else "mm/period"
    assumed = set(row.get("assumed_weather_variables", []))
    def weather_value(key: str, unit: str) -> VariableState:
        return value(row.get(key), unit, Evidence.ASSUMED if key in assumed else evidence,
                     "Normalized forcing metadata/default assumption" if key in assumed else source,
                     "Input artifact omitted this variable; the pre-existing model default was used" if key in assumed else None)
    return {
        "precipitation_mm": weather_value("precip_mm", flux_unit),
        "temperature_c": weather_value("temp_c", "degC"),
        "solar_radiation_mj_m2": weather_value("solar_rad_mj", "MJ/m2/day" if resolution == "DAILY" else "MJ/m2/period"),
        "relative_humidity_percent": weather_value("rh_percent", "percent"),
        "wind_speed_ms": weather_value("wind_speed_ms", "m/s"),
        "potential_et_mm": weather_value("pet_mm", flux_unit),
        "co2_ppm": value(row.get("co2_ppm"), "ppm", Evidence.ASSUMED, "FSPM CO2 forcing assumption"),
    }


def _field(row: dict | None) -> dict[str, VariableState]:
    if row is None:
        return {}
    source = "SimplifiedPlantModel -> PlantToFieldAggregator"
    moisture_source = row.get("soil_moisture_source", "UNSPECIFIED_FSPM_INPUT")
    moisture_assumed = moisture_source.startswith("ASSUMED")
    lai_distribution = row.get("LAI_distribution") or {}
    root_distribution = row.get("root_depth_distribution") or {}
    return {
        "lai": value(row.get("mean_LAI"), "m2_leaf/m2_ground", Evidence.DERIVED, source),
        "lai_p10": value(lai_distribution.get("p10"), "m2_leaf/m2_ground", Evidence.DERIVED, source),
        "lai_p90": value(lai_distribution.get("p90"), "m2_leaf/m2_ground", Evidence.DERIVED, source),
        "lai_std": value(lai_distribution.get("std"), "m2_leaf/m2_ground", Evidence.DERIVED, source),
        "canopy_cover_fraction": value(row.get("canopy_cover"), "fraction", Evidence.DERIVED, source),
        "active_crop_area_fraction": value(row.get("active_crop_area_fraction"), "fraction", Evidence.DERIVED, source),
        "active_calendar_group_count": value(row.get("active_calendar_group_count"), "calendar groups", Evidence.DERIVED, source),
        "calendar_group_count": value(row.get("calendar_group_count"), "calendar groups", Evidence.DERIVED, source),
        "height_m": value(row.get("plant_height_mean_m"), "m", Evidence.DERIVED, source),
        "root_depth_m": value(row.get("root_depth_mean_m"), "m", Evidence.DERIVED, source),
        "root_depth_p10_m": value(root_distribution.get("p10_m"), "m", Evidence.DERIVED, source),
        "root_depth_p90_m": value(root_distribution.get("p90_m"), "m", Evidence.DERIVED, source),
        "representative_plant_count": value(row.get("n_plants"), "modeled representative plants", Evidence.DERIVED, source),
        "biomass_g_plant": value(row.get("biomass_g_plant"), "g/plant", Evidence.DERIVED, source),
        "mean_growing_degree_days": value(row.get("mean_growing_degree_days_c_day"), "degC day", Evidence.DERIVED, source),
        "phenology_fraction": value(row.get("phenology_fraction"), "fraction [0, 1]", Evidence.DERIVED, source),
        "water_stress": value(row.get("water_stress", row.get("mean_stress")), "fraction [0, 1]", Evidence.SIMPLIFIED_FSPM, source),
        "actual_transpiration_mm_day": value(row.get("actual_ET_mm_day"), "mm/day", Evidence.SIMPLIFIED_FSPM, source),
        "potential_transpiration_mm_day": value(row.get("potential_ET_mm_day"), "mm/day", Evidence.SIMPLIFIED_FSPM, source),
        "root_water_uptake_mm_day": value(row.get("soil_water_uptake_mm_day"), "mm/day", Evidence.SIMPLIFIED_FSPM, source),
        "soil_moisture_vol_percent": value(row.get("soil_moisture_vol"), "volumetric percent", Evidence.ASSUMED if moisture_assumed else Evidence.DERIVED if moisture_source.startswith("DERIVED_SWAT") else Evidence.SIMPLIFIED_HYDROLOGY, moisture_source,
                                            "Not derived from SWAT+ soil-water storage" if moisture_source == "ASSUMED_CONSTANT_NOT_SWAT_OUTPUT"
                                            else "Uniform whole-profile storage projected to root zone; no daily layer water states" if moisture_source.startswith("DERIVED_SWAT")
                                            else "Initial configured moisture, before simplified hydrology evolves it" if moisture_source == "ASSUMED_INITIAL_CONDITION" else None),
        "estimated_plant_available_fraction": value(row.get("estimated_plant_available_fraction"), "fraction [0, 1]", Evidence.DERIVED, moisture_source),
        "estimated_root_zone_depth_mm": value(row.get("estimated_root_zone_depth_mm"), "mm", Evidence.DERIVED, moisture_source),
    }


def _plant_samples(states: Iterable[Any], calendar_groups: list[dict] | None = None) -> list[PlantSample]:
    samples = []
    group_hrus = {group["calendar_id"]: [str(hru) for hru in group["hru_ids"]]
                  for group in calendar_groups or []}
    for state in states:
        source = f"PlantPopulation:{state.plant_id}"
        calendar_id = state.plant_id.split(":", 1)[0] if ":" in state.plant_id else None
        samples.append(PlantSample(plant_id=state.plant_id, x_m=state.x_m, y_m=state.y_m,
                                   calendar_id=calendar_id, hru_ids=group_hrus.get(calendar_id, []),
                                   variables={
                                       "lai": value(state.lai, "m2_leaf/m2_ground", Evidence.SIMPLIFIED_FSPM, source),
                                       "height_m": value(state.plant_height_m, "m", Evidence.SIMPLIFIED_FSPM, source),
                                       "root_depth_m": value(state.root_depth_m, "m", Evidence.SIMPLIFIED_FSPM, source),
                                       "leaf_count": value(state.leaf_count, "leaves/plant", Evidence.SIMPLIFIED_FSPM, source),
                                       "leaf_area_m2": value(state.leaf_area_m2, "m2/plant", Evidence.SIMPLIFIED_FSPM, source),
                                       "root_fraction_upper": value(state.root_distribution[0], "fraction", Evidence.SIMPLIFIED_FSPM, source),
                                       "root_fraction_middle": value(state.root_distribution[1], "fraction", Evidence.SIMPLIFIED_FSPM, source),
                                       "root_fraction_lower": value(state.root_distribution[2], "fraction", Evidence.SIMPLIFIED_FSPM, source),
                                       "biomass_g_plant": value(state.biomass_g_plant, "g/plant", Evidence.SIMPLIFIED_FSPM, source),
                                       "phenological_stage": value(state.phenological_stage, "category", Evidence.SIMPLIFIED_FSPM, source),
                                       "water_stress": value(state.stress, "fraction [0, 1]", Evidence.SIMPLIFIED_FSPM, source),
                                       "actual_transpiration_mm_day": value(state.actual_transpiration_mm_day, "mm/day", Evidence.SIMPLIFIED_FSPM, source),
                                       "potential_transpiration_mm_day": value(state.potential_transpiration_mm_day, "mm/day", Evidence.SIMPLIFIED_FSPM, source),
                                       "root_water_uptake_mm_day": value(state.soil_water_uptake_mm_day, "mm/day", Evidence.SIMPLIFIED_FSPM, source),
                                   }))
    return samples


def _hydrology(row: dict, evidence: Evidence, source: str, resolution: str,
               observed_streamflow: float | None = None, observation_source: str | None = None) -> dict[str, VariableState]:
    flux_unit = "mm/day" if resolution == "DAILY" else "mm/period"
    result = {
        "precipitation_mm": value(row.get("precip_mm", row.get("precipitation_mm")), flux_unit, evidence, source),
        "runoff_mm": value(row.get("runoff_mm", row.get("surface_runoff_mm")), flux_unit, evidence, source),
        "runoff_contribution_mm": value(row.get("runoff_contribution_mm"), flux_unit, evidence, source),
        "evapotranspiration_mm": value(row.get("evapotranspiration_mm", row.get("actual_et_mm")), flux_unit, evidence, source),
        "plant_evapotranspiration_mm": value(row.get("plant_evapotranspiration_mm"), flux_unit, evidence, source),
        "soil_evaporation_mm": value(row.get("soil_evaporation_mm"), flux_unit, evidence, source),
        "canopy_evaporation_mm": value(row.get("canopy_evaporation_mm"), flux_unit, evidence, source),
        "potential_evapotranspiration_mm": value(row.get("potential_evapotranspiration_mm"), flux_unit, evidence, source),
        "percolation_mm": value(row.get("percolation_mm"), flux_unit, evidence, source),
        "soil_water_mm": value(row.get("soil_water_mm", row.get("soil_water_depth_mm")), "mm", evidence, source),
        "soil_water_initial_mm": value(row.get("soil_water_initial_mm"), "mm", evidence, source),
        "soil_water_average_mm": value(row.get("soil_water_average_mm"), "mm", evidence, source),
        "streamflow_m3s": value(row.get("streamflow_m3s"), "m3/s", evidence, source),
    }
    if row.get("streamflow_source"):
        result["streamflow_m3s"] = value(row.get("streamflow_m3s"), "m3/s", Evidence.DERIVED, row["streamflow_source"])
    if evidence == Evidence.SIMPLIFIED_HYDROLOGY:
        result["soil_moisture_vol_percent"] = value(row.get("soil_moisture_vol"), "volumetric percent", evidence, source)
    if observation_source:
        result["observed_streamflow_m3s"] = value(observed_streamflow, "m3/s", Evidence.OBSERVED, observation_source)
    return result


def _availability(weather: dict, field: dict, samples: list, hydrology: dict, hrus: list,
                  channels: list | None = None) -> dict[str, str]:
    return {
        "weather": "AVAILABLE" if any(v.availability == "AVAILABLE" for v in weather.values()) else "NOT_AVAILABLE",
        "field": "AVAILABLE" if any(v.availability == "AVAILABLE" for v in field.values()) else "NOT_AVAILABLE",
        "plant_samples": "AVAILABLE" if samples else "NOT_AVAILABLE",
        "hydrology": "AVAILABLE" if any(v.availability == "AVAILABLE" for v in hydrology.values()) else "NOT_AVAILABLE",
        "hru_results": "AVAILABLE" if hrus else "NOT_AVAILABLE",
        "channel_results": "AVAILABLE" if channels else "NOT_AVAILABLE",
    }


def _weather_by_period(forcing: list[dict], resolution: str) -> dict[str, dict]:
    grouped: dict[str, list[dict]] = defaultdict(list)
    seen = set()
    for row in forcing:
        day = date.fromisoformat(row["date"])
        if day in seen:
            raise ValueError(f"Duplicate forcing date {day}")
        seen.add(day)
        key = day.isoformat() if resolution == "DAILY" else day.strftime("%Y-%m-01") if resolution == "MONTHLY" else f"{day.year}-01-01"
        grouped[key].append(row)
    result = {}
    for key, rows in grouped.items():
        if resolution == "DAILY":
            result[key] = rows[0]
        else:
            result[key] = {
                "precip_mm": sum(row["precip_mm"] for row in rows),
                "temp_c": fmean(row["temp_c"] for row in rows),
                "solar_rad_mj": sum(row["solar_rad_mj"] for row in rows) if all(row.get("solar_rad_mj") is not None for row in rows) else None,
                "rh_percent": fmean(row["rh_percent"] for row in rows) if all(row.get("rh_percent") is not None for row in rows) else None,
                "wind_speed_ms": fmean(row["wind_speed_ms"] for row in rows) if all(row.get("wind_speed_ms") is not None for row in rows) else None,
                "pet_mm": sum(row["pet_mm"] for row in rows) if all(row.get("pet_mm") is not None for row in rows) else None,
                "co2_ppm": rows[0].get("co2_ppm"),
                "assumed_weather_variables": sorted({name for row in rows for name in row.get("assumed_weather_variables", [])}),
                "forcing_day_count": len(rows),
            }
    return result


def swat_frames(*, simulation_id: str, watershed_id: str, run_type: str,
                resolution: str, records: list[dict], hru_results: list[dict],
                plant_results: list[dict] | None = None,
                channel_results: list[dict] | None = None,
                soil_profiles: dict[int, SoilProfile] | None = None,
                hru_gis_ids: dict[int, str] | None = None,
                hru_calendar: dict[int, dict] | None = None,
                forcing: list[dict] | None, forcing_source: str,
                watershed_code: str | None = None, outlet_unit: str | None = None,
                fspm_days: dict[str, dict] | None = None,
                start_date: date | None = None, end_date: date | None = None,
                missing_hydrology_reason: str = "SWAT+ has no normalized output for this period; hydrological values are null",
                observations: dict[str, float] | None = None,
                observation_source: str | None = None) -> Iterable[PlaybackRecord]:
    weather_by_date = _weather_by_period(forcing or [], resolution)
    observations_by_period: dict[str, list[float]] = defaultdict(list)
    for observed_day, flow in (observations or {}).items():
        parsed_day = date.fromisoformat(observed_day)
        observed_period = parsed_day.isoformat() if resolution == "DAILY" else parsed_day.strftime("%Y-%m-01") if resolution == "MONTHLY" else f"{parsed_day.year}-01-01"
        observations_by_period[observed_period].append(flow)
    hrus_by_date: dict[str, list[dict]] = defaultdict(list)
    for row in hru_results:
        hrus_by_date[row["period"]].append(row)
    channels_by_date: dict[str, list[dict]] = defaultdict(list)
    channel_keys = set()
    for row in channel_results or []:
        key = (row["period"], str(row["channel_unit"]))
        if key in channel_keys:
            raise ValueError(f"Duplicate SWAT+ channel output {key}")
        channel_keys.add(key)
        channels_by_date[row["period"]].append(row)
    plants_by_date_hru: dict[tuple[str, str], dict] = {}
    for row in plant_results or []:
        identifier = row.get("hru_unit", row.get("hru_gis_id"))
        if identifier is not None:
            key = (row["period"], str(identifier))
            if key in plants_by_date_hru:
                raise ValueError(f"Duplicate SWAT+ plant output for period/HRU {key}")
            plants_by_date_hru[key] = row
    by_period = {}
    for row in records:
        day = row["period"]
        if day in by_period:
            raise ValueError(f"Duplicate SWAT+ output date {day}")
        by_period[day] = row
    if (start_date is None) != (end_date is None):
        raise ValueError("Both requested interval boundaries are required")
    if start_date is not None:
        if end_date < start_date:
            raise ValueError("Requested interval is reversed")
        requested = set()
        cursor = start_date
        while cursor <= end_date:
            requested.add(cursor.isoformat() if resolution == "DAILY" else cursor.strftime("%Y-%m-01") if resolution == "MONTHLY" else f"{cursor.year}-01-01")
            cursor += timedelta(days=1)
        if (set(by_period) | set(weather_by_date) | set(hrus_by_date)) - requested:
            raise ValueError("A forcing or SWAT+ period falls outside the requested interval")
        periods = sorted(requested)
    else:
        periods = sorted(set(by_period) | set(weather_by_date) | set(hrus_by_date))
    for day in periods:
        row = by_period.get(day, {})
        field_day = (fspm_days or {}).get(day) if resolution == "DAILY" else None
        field_values = _field(field_day["field"]) if field_day and field_day.get("field") else {}
        samples = _plant_samples(field_day.get("plants", []), field_day.get("calendar_groups")) if field_day else []
        sample_context = field_day.get("plant_sample_context") if field_day else None
        crop = CropState(**field_day["crop"]) if field_day and field_day.get("crop") else None
        hru_states = []
        for hru in hrus_by_date.get(day, []):
            identifier = hru.get("hru_unit")
            if identifier is None:
                continue
            variables = _hydrology(hru, Evidence.MODELLED_SWAT_PLUS, "SWAT+ HRU output", resolution)
            profile = (soil_profiles or {}).get(int(identifier))
            if profile is not None and hru.get("soil_water_average_mm") is not None:
                root_depth = (field_day or {}).get("hru_water", {}).get(str(identifier), {}).get("estimated_root_zone_depth_mm")
                estimate = hru_water_state(profile, float(hru["soil_water_average_mm"]),
                                           float(root_depth) / 1000.0 if root_depth is not None else profile.depth_mm / 1000.0)
                for name, unit in (("estimated_soil_moisture_vol_percent", "volumetric percent"),
                                   ("estimated_plant_available_fraction", "fraction [0, 1]"),
                                   ("estimated_root_zone_water_mm", "mm"),
                                   ("estimated_root_zone_depth_mm", "mm")):
                    variables[name] = value(estimate[name], unit, Evidence.DERIVED,
                                            "SWAT+ hru_wb_day.sw_ave + hru-data.hru + soils.sol",
                                            "SWAT+ storage excludes wilting-point water; uniform available-water fraction across layers; daily layer water is not printed")
            plant = plants_by_date_hru.get((day, str(identifier)))
            if plant is not None:
                plant_units = {
                    "lai_m2_m2": "m2_leaf/m2_ground", "biomass_kg_ha": "kg/ha",
                    "yield_kg_ha": "kg/ha", "water_stress_factor": "fraction [0, 1]",
                    "aeration_stress_factor": "fraction [0, 1]", "temperature_stress_factor": "fraction [0, 1]",
                    "nitrogen_stress_factor": "fraction [0, 1]", "phosphorus_stress_factor": "fraction [0, 1]",
                    "salinity_stress_factor": "fraction [0, 1]", "plant_heat_unit_fraction": "fraction [0, 1]",
                    "biomass_growth_kg_ha": "kg/ha/day",
                }
                variables.update({
                    f"swat_{name}": value(plant.get(name), unit, Evidence.MODELLED_SWAT_PLUS,
                                          "SWAT+ hru_pw output")
                    for name, unit in plant_units.items()
                })
            calendar = (hru_calendar or {}).get(int(identifier))
            hru_crop = None
            if calendar is not None:
                active = calendar["planting_date"] <= day <= calendar["harvest_date"]
                hru_crop = CropState(active=active, crop="maize" if active else None,
                                     season_id=calendar["calendar_id"],
                                     window_status="EXECUTED_SWAT_MANAGEMENT_EVENTS" if active else "NO_ACTIVE_EXECUTED_CROP_CALENDAR",
                                     source="SWAT+ mgt_out.txt PLANT and HARV/KILL")
            hru_states.append(HruState(hru_id=str(identifier), spatial_support="SWAT_HRU_OUTPUT_UNIT_NO_VERIFIED_POLYGON",
                                       gis_id=(hru_gis_ids or {}).get(int(identifier),
                                              str(hru["hru_gis_id"]) if hru.get("hru_gis_id") is not None else None),
                                       calendar_id=calendar["calendar_id"] if calendar else None,
                                       crop=hru_crop, variables=variables))
        channel_states = []
        channel_units = {
            "streamflow_m3s": "m3/s", "channel_inflow_m3s": "m3/s",
            "channel_water_storage_m3": "m3", "channel_precip_volume_m3": "m3/day",
            "channel_evap_volume_m3": "m3/day", "channel_seep_volume_m3": "m3/day",
            "channel_water_temp_c": "degC", "channel_area_ha": "ha",
        }
        for channel in channels_by_date.get(day, []):
            channel_states.append(ChannelState(
                channel_id=str(channel["channel_unit"]),
                gis_id=str(channel["channel_gis_id"]) if channel.get("channel_gis_id") is not None else None,
                variables={name: value(channel.get(name), unit,
                                       Evidence.DERIVED if channel.get("streamflow_source") and name in {"streamflow_m3s", "channel_inflow_m3s"} else Evidence.MODELLED_SWAT_PLUS,
                                       channel["streamflow_source"] if channel.get("streamflow_source") and name in {"streamflow_m3s", "channel_inflow_m3s"} else "SWAT+ channel_sd_day")
                           for name, unit in channel_units.items()},
            ))
        weather = _weather(weather_by_date.get(day), resolution=resolution, source=forcing_source, evidence=Evidence.DERIVED)
        observed_values = observations_by_period.get(day, [])
        hydro = _hydrology(row, Evidence.MODELLED_SWAT_PLUS, "SWAT+ normalized output", resolution,
                           fmean(observed_values) if observed_values else None,
                           f"{observation_source}; mean of linked daily values" if observation_source and resolution != "DAILY" else observation_source)
        if observed_values and resolution != "DAILY":
            hydro["observed_streamflow_m3s"].limitation = (
                f"Mean of {len(observed_values)} available observed days in the requested interval; completeness not assumed"
            )
        limitations = []
        if day not in weather_by_date:
            limitations.append("Weather forcing unavailable for this output period; no precipitation is inferred from runoff")
        else:
            forcing_day_count = weather_by_date[day].get("forcing_day_count", 1)
            period_date = date.fromisoformat(day)
            expected_days = (monthrange(period_date.year, period_date.month)[1] if resolution == "MONTHLY"
                             else 366 if resolution == "ANNUAL" and isleap(period_date.year)
                             else 365 if resolution == "ANNUAL" else 1)
            if forcing_day_count < expected_days:
                limitations.append(
                    f"Weather is aggregated from {forcing_day_count} available forcing days of {expected_days} calendar-period days; no missing daily forcing is reconstructed"
                )
        if day not in by_period:
            limitations.append(missing_hydrology_reason)
        if run_type == "SWAT_MULTISCALE_COUPLED" and resolution != "DAILY":
            limitations.append("Daily FSPM states are not attached to aggregated SWAT+ output periods")
        if field_day and crop and crop.window_status == "EXECUTED_SWAT_MANAGEMENT_EVENTS":
            limitations.append("FSPM calendar follows SWAT+ executed HRU events; the field state is an area-weighted composite of distinct calendar groups")
        yield PlaybackRecord(simulation_id=simulation_id, date=date.fromisoformat(day), resolution=resolution,
                             run_type=run_type, watershed_id=watershed_id, watershed_code=watershed_code,
                             outlet_unit=outlet_unit, spatial_support="WATERSHED_OUTLET_AND_BASIN",
                             weather=weather, crop=crop, field=field_values, plant_samples=samples,
                             plant_sample_context=sample_context,
                             hydrology=hydro, hru_results=hru_states, channel_results=channel_states,
                             availability=_availability(weather, field_values, samples, hydro, hru_states, channel_states),
                             limitations=limitations)


def simplified_frames(*, simulation_id: str, watershed_id: str, rows: Iterable[dict],
                      daily_fields: Iterable[dict], climate_source: str,
                      watershed_code: str | None = None,
                      observations: dict[str, float] | None = None,
                      observation_source: str | None = None) -> Iterable[PlaybackRecord]:
    weather_evidence = Evidence.SYNTHETIC if climate_source == "SYNTHETIC" else Evidence.DERIVED
    for row, state in zip(rows, daily_fields, strict=True):
        day = row["date_str"]
        if state["date"] != day:
            raise ValueError(f"FSPM and simplified hydrology dates do not align: {state['date']} != {day}")
        weather = _weather(row, resolution="DAILY", source=climate_source, evidence=weather_evidence)
        field_values = _field(state["field"])
        samples = _plant_samples(state["plants"])
        hydro = _hydrology(row, Evidence.SIMPLIFIED_HYDROLOGY, "SimplifiedHydrologyModel", "DAILY",
                           (observations or {}).get(day), observation_source)
        yield PlaybackRecord(simulation_id=simulation_id, date=date.fromisoformat(day), resolution="DAILY",
                             run_type="RESEARCH_MULTISCALE", watershed_id=watershed_id, watershed_code=watershed_code,
                             spatial_support="COARSE_HRU_PROXY", weather=weather,
                             crop=CropState(active=True, crop=state["crop"], phenological_stage=state["phenological_stage"],
                                            source="SimplifiedPlantModel", limitation="No explicit crop-management season in the simplified run"),
                             field=field_values, plant_samples=samples, hydrology=hydro,
                             plant_sample_context=state.get("plant_sample_context"),
                             availability=_availability(weather, field_values, samples, hydro, []),
                             limitations=["Coarse HRUs have no verified SWAT+ polygon identity"])
