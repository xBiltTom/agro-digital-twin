"""Manual real-SWAT+ integration runner for the official Ames corn reference.

It is deliberately outside application flow; API tests exercise the application
flow.  This records a reproducible paired execution when SWAT+ is locally present.
"""
from datetime import date
from pathlib import Path
import json
import os
import threading
import time

from app.services.swat_plus_adapter import SwatPlusAdapter, SwatPlusRunConfig
from app.services.swat_plant_parameter_mapper import SwatClimateForcingReader, SwatPlantParameterMapper
from scientific_core import PlantPopulation, PlantToFieldAggregator

project = Path(os.environ["SWAT_PLUS_COUPLED_PROJECT"])
executable = Path(os.environ["SWAT_PLUS_EXECUTABLE"])
workspaces = Path(os.environ.get("SWAT_PLUS_COUPLED_WORKDIR", "/tmp/swatplus-paired-runs"))
start, end = date.fromisoformat(os.environ.get("SWAT_PLUS_COUPLED_START", "1982-01-01")), date.fromisoformat(os.environ.get("SWAT_PLUS_COUPLED_END", "1982-12-31"))

climate, forcing_provenance = SwatClimateForcingReader(project).for_period(start, end)
population, gdd, peak = PlantPopulation(1000, 42), 0.0, None
for index, forcing in enumerate(climate, 1):
    gdd += max(0.0, forcing["temp_c"] - 8.0)
    state = population.step(index, {**forcing, "gdd_c_day": gdd}, .24)
    aggregate = PlantToFieldAggregator.aggregate(state, .24)
    if peak is None or aggregate["mean_LAI"] > peak["mean_LAI"]:
        peak = aggregate

adapter = SwatPlusAdapter()
common = dict(project_path=project, executable_path=executable, working_directory=workspaces, simulation_start=start, simulation_end=end, warmup_period=0, output_frequency="DAILY", watershed_id="AMES", timeout_seconds=900)
result, failure = {}, []

def run_pair():
    try:
        if not os.getenv("SWAT_SKIP_BASELINE"):
            result["baseline"] = adapter.run(SwatPlusRunConfig(**common, run_id="ames-1982-baseline", run_type="SWAT_STANDARD_BASELINE"))
        result["coupled"] = adapter.run(SwatPlusRunConfig(**common, run_id="ames-1982-coupled", run_type="SWAT_MULTISCALE_COUPLED"), workspace_mutator=lambda workspace: SwatPlantParameterMapper("corn").apply(workspace, peak))
    except BaseException as exc:
        failure.append(exc)

thread = threading.Thread(target=run_pair, daemon=False)
thread.start()
while thread.is_alive():
    print("annual paired SWAT+ run in progress", flush=True)
    time.sleep(5)
thread.join()
if failure:
    raise failure[0]
baseline, coupled = result.get("baseline"), result["coupled"]
print(json.dumps({"forcing": forcing_provenance, "field": peak, "baseline": None if baseline is None else {"run_id": baseline.run_id, "exit_code": baseline.exit_code, "water_balance": baseline.water_balance, "provenance": baseline.provenance}, "coupled": {"run_id": coupled.run_id, "exit_code": coupled.exit_code, "water_balance": coupled.water_balance, "provenance": coupled.provenance}}, default=str))
