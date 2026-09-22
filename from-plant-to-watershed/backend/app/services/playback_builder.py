"""Compose dated FSPM, forcing and hydrology without inventing missing states."""

from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta
from statistics import fmean
from typing import Any, Iterable

from app.schemas.playback import CropState, Evidence, HruState, PlaybackRecord, PlantSample, VariableState


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
    return {
        "lai": value(row.get("mean_LAI"), "m2_leaf/m2_ground", Evidence.DERIVED, source),
        "canopy_cover_fraction": value(row.get("canopy_cover"), "fraction", Evidence.DERIVED, source),
        "height_m": value(row.get("plant_height_mean_m"), "m", Evidence.DERIVED, source),
        "root_depth_m": value(row.get("root_depth_mean_m"), "m", Evidence.DERIVED, source),
        "biomass_g_plant": value(row.get("biomass_g_plant"), "g/plant", Evidence.DERIVED, source),
        "phenology_fraction": value(row.get("phenology_fraction"), "fraction [0, 1]", Evidence.DERIVED, source),
        "water_stress": value(row.get("water_stress"), "fraction [0, 1]", Evidence.SIMPLIFIED_FSPM, source),
        "actual_transpiration_mm_day": value(row.get("actual_ET_mm_day"), "mm/day", Evidence.SIMPLIFIED_FSPM, source),
        "potential_transpiration_mm_day": value(row.get("potential_ET_mm_day"), "mm/day", Evidence.SIMPLIFIED_FSPM, source),
        "root_water_uptake_mm_day": value(row.get("soil_water_uptake_mm_day"), "mm/day", Evidence.SIMPLIFIED_FSPM, source),
        "soil_moisture_vol_percent": value(row.get("soil_moisture_vol"), "volumetric percent", Evidence.ASSUMED if moisture_assumed else Evidence.SIMPLIFIED_HYDROLOGY, moisture_source,
                                            "Not derived from SWAT+ soil-water storage" if moisture_source == "ASSUMED_CONSTANT_NOT_SWAT_OUTPUT"
                                            else "Initial configured moisture, before simplified hydrology evolves it" if moisture_source == "ASSUMED_INITIAL_CONDITION" else None),
    }


def _plant_samples(states: Iterable[Any]) -> list[PlantSample]:
    samples = []
    for state in states:
        source = f"PlantPopulation:{state.plant_id}"
        samples.append(PlantSample(plant_id=state.plant_id, x_m=state.x_m, y_m=state.y_m,
                                   variables={
                                       "lai": value(state.lai, "m2_leaf/m2_ground", Evidence.SIMPLIFIED_FSPM, source),
                                       "height_m": value(state.plant_height_m, "m", Evidence.SIMPLIFIED_FSPM, source),
                                       "root_depth_m": value(state.root_depth_m, "m", Evidence.SIMPLIFIED_FSPM, source),
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
        "runoff_mm": value(row.get("runoff_mm", row.get("surface_runoff_mm")), flux_unit, evidence, source),
        "evapotranspiration_mm": value(row.get("evapotranspiration_mm", row.get("actual_et_mm")), flux_unit, evidence, source),
        "percolation_mm": value(row.get("percolation_mm"), flux_unit, evidence, source),
        "soil_water_mm": value(row.get("soil_water_mm", row.get("soil_water_depth_mm")), "mm", evidence, source),
        "streamflow_m3s": value(row.get("streamflow_m3s"), "m3/s", evidence, source),
    }
    if evidence == Evidence.SIMPLIFIED_HYDROLOGY:
        result["soil_moisture_vol_percent"] = value(row.get("soil_moisture_vol"), "volumetric percent", evidence, source)
    if observation_source:
        result["observed_streamflow_m3s"] = value(observed_streamflow, "m3/s", Evidence.OBSERVED, observation_source)
    return result


def _availability(weather: dict, field: dict, samples: list, hydrology: dict, hrus: list) -> dict[str, str]:
    return {
        "weather": "AVAILABLE" if any(v.availability == "AVAILABLE" for v in weather.values()) else "NOT_AVAILABLE",
        "field": "AVAILABLE" if any(v.availability == "AVAILABLE" for v in field.values()) else "NOT_AVAILABLE",
        "plant_samples": "AVAILABLE" if samples else "NOT_AVAILABLE",
        "hydrology": "AVAILABLE" if any(v.availability == "AVAILABLE" for v in hydrology.values()) else "NOT_AVAILABLE",
        "hru_results": "AVAILABLE" if hrus else "NOT_AVAILABLE",
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
            }
    return result


def swat_frames(*, simulation_id: str, watershed_id: str, run_type: str,
                resolution: str, records: list[dict], hru_results: list[dict],
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
        samples = _plant_samples(field_day.get("plants", [])) if field_day else []
        crop = CropState(**field_day["crop"]) if field_day and field_day.get("crop") else None
        hru_states = []
        for hru in hrus_by_date.get(day, []):
            identifier = hru.get("hru_unit")
            if identifier is None:
                continue
            hru_states.append(HruState(hru_id=str(identifier), spatial_support="SWAT_HRU_OUTPUT_UNIT_NO_VERIFIED_POLYGON",
                                       variables=_hydrology(hru, Evidence.MODELLED_SWAT_PLUS, "SWAT+ HRU output", resolution)))
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
        if day not in by_period:
            limitations.append(missing_hydrology_reason)
        if run_type == "SWAT_MULTISCALE_COUPLED" and resolution != "DAILY":
            limitations.append("Daily FSPM states are not attached to aggregated SWAT+ output periods")
        if field_day and crop and crop.window_status == "APPROXIMATE_PLANTING_WINDOW":
            limitations.append("Crop window approximates SWAT+ auto-management; executed event date is unavailable")
        yield PlaybackRecord(simulation_id=simulation_id, date=date.fromisoformat(day), resolution=resolution,
                             run_type=run_type, watershed_id=watershed_id, watershed_code=watershed_code,
                             outlet_unit=outlet_unit, spatial_support="WATERSHED_OUTLET_AND_BASIN",
                             weather=weather, crop=crop, field=field_values, plant_samples=samples,
                             hydrology=hydro, hru_results=hru_states,
                             availability=_availability(weather, field_values, samples, hydro, hru_states),
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
                             availability=_availability(weather, field_values, samples, hydro, []),
                             limitations=["Coarse HRUs have no verified SWAT+ polygon identity"])
