"""Project catalogue metadata in SQL without loading scientific result arrays."""

from sqlalchemy import JSON, column, func, select, true

from app.models.simulation import ClimateScenario, SimulationRun


CATALOG_FIELDS = (
    "id", "user_id", "watershed_id", "scenario_id", "name", "status",
    "duration_days", "irrigation_efficiency", "seed", "started_at", "finished_at",
    "mode", "plant_count", "hydrology_backend", "external_model_id",
    "management_scenario", "climate_source", "station_id", "start_date", "end_date",
    "created_at",
)
SCENARIO_FIELDS = (
    "id", "code", "name", "pathway", "description", "temp_anomaly_c",
    "precip_factor", "co2_ppm", "source_type",
)
# Preserve evidence precedence, including historical-import markers. Do not select
# the whole JSON document: some runs contain hundreds of MB of HRU results/logs.
JSON_PATHS = {
    "provenance": (
        ("evidence_type",), ("source_kind",), ("run_evidence_type",),
        ("experiment_id",), ("experiment", "experiment_id"), ("experiment", "id"),
        ("lineage", "experiment_id"), ("hydrology", "model"), ("plant", "model"),
    ),
    "requested_config": (("swat_plus", "run_type"), ("swat_plus", "experiment_id")),
    "effective_config": (("run_type",), ("experiment_id",), ("backend",)),
    "summary_metrics": tuple((key,) for key in (
        "total_precip_mm", "total_precipitation_mm", "total_discharge_hm3",
        "total_actual_et_mm", "total_evapotranspiration_mm", "total_surface_runoff_mm",
        "total_runoff_mm", "mean_streamflow_m3s", "peak_streamflow_m3s", "mean_cwsi",
        "seasonal_crop_yield_proxy_t_ha", "evidence_type", "experiment_id",
    )) + (("water_balance", "mean_streamflow_m3s"),
          ("water_balance", "totals_mm", "precip_mm"),
          ("water_balance", "totals_mm", "evapotranspiration_mm"),
          ("water_balance", "totals_mm", "runoff_mm")),
    "error": (("message",), ("type",), ("code",)),
}


def catalog_query(dialect_name="sqlite"):
    columns = [getattr(SimulationRun, key) for key in CATALOG_FIELDS]
    columns += [getattr(ClimateScenario, key).label(f"catalog_scenario_{key}") for key in SCENARIO_FIELDS]
    projections = []
    for group, paths in JSON_PATHS.items():
        projection = None
        if dialect_name == "postgresql":
            # The legacy columns use JSON, so separate -> expressions would
            # repeatedly parse the same (potentially large) document. Extract
            # all requested top-level keys in one pass with json_to_record.
            top_keys = dict.fromkeys(path[0] for path in paths)
            projection = func.json_to_record(getattr(SimulationRun, group)).table_valued(
                *(column(key, JSON) for key in top_keys)
            ).render_derived(name=f"catalog_{group}", with_types=True).lateral()
            projections.append(projection)
        for path in paths:
            expression = projection.c[path[0]] if projection is not None else getattr(SimulationRun, group)
            for key in path[1:] if projection is not None else path:
                expression = expression[key]
            columns.append(expression.label("__".join((group, *path))))
    statement = select(*columns).select_from(SimulationRun).outerjoin(ClimateScenario, SimulationRun.scenario_id == ClimateScenario.id)
    for projection in projections:
        statement = statement.outerjoin(projection, true())
    return statement


def catalog_entry(row):
    entry = {key: row[key] for key in CATALOG_FIELDS}
    entry["scenario"] = (
        {key: row[f"catalog_scenario_{key}"] for key in SCENARIO_FIELDS}
        if row["catalog_scenario_id"] is not None else None
    )
    for group, paths in JSON_PATHS.items():
        values = {}
        for path in paths:
            value = row["__".join((group, *path))]
            if value is None:
                continue
            target = values
            for key in path[:-1]:
                target = target.setdefault(key, {})
            target[path[-1]] = value
        entry[group] = values
    return entry
