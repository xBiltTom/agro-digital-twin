"""Export reproducible monthly rows for the independent training laboratory."""

from __future__ import annotations

import csv
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.simulation import SimulationResult, SimulationRun


SCHEMA_VERSION = "plant-to-watershed-training-export/v1"
FIELDNAMES = [
    "date", "watershed_id", "hru_id", "run_id", "precip_mm", "temp_mean_c", "solar_radiation",
    "soil_moisture", "infiltration_mm", "lai", "root_depth_m", "transpiration_mm", "water_stress", "et_mm",
    "baseline_streamflow_m3s", "multiscale_twin_streamflow_m3s", "observed_streamflow_m3s",
    "ml_assisted_streamflow_m3s", "ml_assisted_runoff_mm", "dataset_roles", "provenance",
]


async def export_training_dataset(db: AsyncSession, run_ids: list[str], output_dir: str | Path) -> tuple[Path, Path, int]:
    if not run_ids:
        raise ValueError("at least one run_id is required")
    runs = list((await db.execute(select(SimulationRun).where(SimulationRun.id.in_(run_ids)))).scalars().all())
    missing = set(run_ids) - {run.id for run in runs}
    if missing:
        raise ValueError(f"unknown run IDs: {', '.join(sorted(missing))}")
    records: list[dict[str, Any]] = []
    for run in runs:
        results = list((await db.execute(select(SimulationResult).where(SimulationResult.simulation_run_id == run.id)
                                         .order_by(SimulationResult.day_index))).scalars().all())
        by_month: dict[str, list[SimulationResult]] = defaultdict(list)
        for result in results:
            by_month[result.date_str[:7]].append(result)
        monthly = {row["month"]: row for row in (run.monthly_outputs or [])}
        field = run.field_aggregates or {}
        for month, days in sorted(by_month.items()):
            output = monthly.get(month, {})
            records.append({
                "date": month, "watershed_id": run.watershed_id, "hru_id": "WATERSHED_AREA_WEIGHTED_PROXY",
                "run_id": run.id, "precip_mm": sum(day.precip_mm for day in days),
                "temp_mean_c": sum(day.temp_c for day in days) / len(days),
                "solar_radiation": sum(day.solar_rad_mj for day in days) / len(days),
                "soil_moisture": sum(day.soil_moisture_vol for day in days) / len(days),
                "infiltration_mm": sum(max(0.0, day.precip_mm - day.surface_runoff_mm) for day in days),
                "lai": field.get("mean_lai"), "root_depth_m": (field.get("mean_root_depth_cm") or 0) / 100,
                "transpiration_mm": sum(day.plant_transpiration_mm for day in days),
                "water_stress": sum(day.cwsi_stress_index for day in days) / len(days),
                "et_mm": sum(day.actual_et_mm for day in days),
                "baseline_streamflow_m3s": output.get("baseline_streamflow_m3s"),
                "multiscale_twin_streamflow_m3s": output.get("twin_streamflow_m3s"),
                "observed_streamflow_m3s": output.get("observed_streamflow_m3s"),
                "ml_assisted_streamflow_m3s": output.get("ml_assisted_streamflow_m3s"),
                "ml_assisted_runoff_mm": output.get("ml_assisted_runoff_mm"),
                "dataset_roles": json.dumps(run.dataset_roles or {}, sort_keys=True),
                "provenance": json.dumps({"run_evidence": (run.provenance or {}).get("run_evidence_type"),
                                            "climate_source": run.climate_source, "station_id": run.station_id,
                                            "field_state": "final-run aggregate; not a per-HRU observation"}, sort_keys=True),
            })
    directory = Path(output_dir).resolve()
    directory.mkdir(parents=True, exist_ok=True)
    data_path, manifest_path = directory / "multiscale_training_dataset.csv", directory / "manifest.json"
    with data_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(records)
    manifest_path.write_text(json.dumps({
        "schema_version": SCHEMA_VERSION, "created_at": datetime.now(timezone.utc).isoformat(),
        "format": "csv", "data_file": data_path.name, "row_count": len(records), "run_ids": sorted(run_ids),
        "units": {"precip_mm": "mm/month", "temp_mean_c": "degC", "solar_radiation": "MJ/m2/day",
                  "soil_moisture": "percent_vol", "root_depth_m": "m", "streamflow": "m3/s"},
        "limitations": ["Rows retain source provenance.", "Field LAI/root depth are run aggregates, not observed HRU states.",
                        "Synthetic-trained model metrics must not be interpreted as H1 evidence."],
    }, indent=2), encoding="utf-8")
    return data_path, manifest_path, len(records)
