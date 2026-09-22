import json
from pathlib import Path
from types import SimpleNamespace

import pytest


def test_corrected_runner_writes_a_v3_dataset_schema(tmp_path, monkeypatch):
    pytest.importorskip("pyarrow")
    import scripts.run_final_south_fork as runner

    monkeypatch.setattr(runner, "ROOT", tmp_path)
    day = "2018-01-01"
    records = [{"period": day, "streamflow_m3s": 1.0, "runoff_mm": 2.0,
                "evapotranspiration_mm": 3.0, "soil_water_mm": 100.0}]
    field = {day: {"precipitation_mm": 4.0, "temperature_min": 5.0, "temperature_max": 6.0,
                   "FSPM_LAI": 1.0, "FSPM_root_depth": .2, "FSPM_biomass": 3.0,
                   "FSPM_water_stress": 0.1}}
    _, schema_path = runner._write_dataset(SimpleNamespace(records=records, run_id="baseline"), SimpleNamespace(records=records, run_id="coupled"), {day: 1.0}, field)
    schema = json.loads(Path(schema_path).read_text(encoding="utf-8"))
    assert schema["schema_version"] == "south-fork-final-v3"
    assert schema["contract_version"] == "south-fork-final-v3"
    assert Path(schema_path).name == "experiment_dataset_v3.schema.json"


def test_historical_v2_status_remains_executed_and_v1_archived():
    status_path = Path(__file__).parents[2] / "research_domain" / "current_contract_status.json"
    status = json.loads(status_path.read_text(encoding="utf-8"))
    assert status["current_contract"]["contract_version"] == "south-fork-final-v2"
    assert status["current_contract"]["current_execution_status"] == "EXECUTED"
    assert status["current_contract"]["result_path"] == "research_domain/final_report_v2.json"
    assert status["archived_result"]["report_version"] == "south-fork-final-v1"
    assert status["archived_result"]["status"] == "ARCHIVED_HISTORICAL_RESULT"
