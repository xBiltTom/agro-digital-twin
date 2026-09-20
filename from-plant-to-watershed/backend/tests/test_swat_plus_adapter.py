from datetime import date
import os
from pathlib import Path
import hashlib

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.models.simulation import ClimateScenario, SimulationRun
from app.models.user import User
from app.models.watershed import Watershed
from app.services.swat_plus_adapter import (
    SwatExecutableNotFoundError,
    SwatOutputNotFoundError,
    SwatPlusAdapter,
    SwatPlusRunConfig,
    SwatProjectInvalidError,
    SwatProjectNotFoundError,
    SwatRunFailedError,
)
from app.services.swat_plus_parser import SwatOutputParser
from app.services.twin_coupling_engine import TwinCouplingEngine
from app.main import app


def _project(tmp_path: Path) -> Path:
    project = tmp_path / "source-project"
    project.mkdir()
    (project / "file.cio").write_text("SWAT+ input fixture\n", encoding="utf-8")
    (project / "time.sim").write_text(
        "time.sim fixture\n"
        "day_start yrc_start day_end yrc_end step\n"
        "1 2019 365 2019 0\n", encoding="utf-8",
    )
    (project / "print.prt").write_text(
        "print.prt fixture\n"
        "nyskip day_start yrc_start day_end yrc_end interval\n"
        "0 0 2019 0 2019 1\n"
        "aa_int_cnt\n0\n"
        "csvout dbout cdfout\nn n n\n"
        "soilout mgtout hydcon fdcout\nn n n n\n"
        "objects daily monthly yearly avann\n"
        "basin_wb n n y y\n"
        "hru_wb n n n y\n"
        "channel n n n y\n"
        "channel_sd n n n y\n", encoding="utf-8",
    )
    return project


def _executable(tmp_path: Path, body: str = "exit 0") -> Path:
    executable = tmp_path / "swat-plus-fixture"
    executable.write_text(f"#!/bin/sh\n{body}\n", encoding="utf-8")
    executable.chmod(0o755)
    return executable


def _config(tmp_path: Path, project: Path, executable: Path, run_id: str = "run-001") -> SwatPlusRunConfig:
    return SwatPlusRunConfig(
        project_path=project, executable_path=executable, working_directory=tmp_path / "workspaces",
        simulation_start=date(2020, 1, 1), simulation_end=date(2020, 1, 2), warmup_period=0,
        output_frequency="DAILY", watershed_id="fixture-watershed", run_id=run_id, timeout_seconds=10,
    )


def test_valid_swat_configuration_is_accepted(tmp_path: Path):
    config = _config(tmp_path, _project(tmp_path), _executable(tmp_path))
    config.validate()


def test_missing_executable_has_stable_error_code(tmp_path: Path):
    config = _config(tmp_path, _project(tmp_path), tmp_path / "missing-swat")
    with pytest.raises(SwatExecutableNotFoundError, match="not found") as raised:
        SwatPlusAdapter().run(config)
    assert raised.value.code == "SWAT_EXECUTABLE_NOT_FOUND"


def test_missing_project_has_stable_error_code(tmp_path: Path):
    config = _config(tmp_path, tmp_path / "missing-project", _executable(tmp_path))
    with pytest.raises(SwatProjectNotFoundError) as raised:
        SwatPlusAdapter().run(config)
    assert raised.value.code == "SWAT_PROJECT_NOT_FOUND"


def test_declared_missing_weather_input_is_rejected_before_workspace_creation(tmp_path: Path):
    project = _project(tmp_path)
    (project / "weather-sta.cli").write_text(
        "weather stations\nname wgn pcp tmp slr hmd wnd\nstation wgn pcp.dat tmp.dat sim sim sim\n",
        encoding="utf-8",
    )
    config = _config(tmp_path, project, _executable(tmp_path))
    with pytest.raises(SwatProjectInvalidError, match="weather files") as raised:
        SwatPlusAdapter().run(config)
    assert raised.value.code == "SWAT_PROJECT_INVALID"
    assert raised.value.details["missing_weather_files"] == ["pcp.dat", "tmp.dat"]
    assert not (tmp_path / "workspaces" / config.run_id).exists()


def test_parser_normalizes_units_and_keeps_only_actual_columns(tmp_path: Path):
    (tmp_path / "output_wb_day").write_text(
        "yr mon day surq et perc sw\n"
        "yyyy mm dd mm mm m mm\n"
        "2020 1 1 2.5 3.0 0.004 180\n",
        encoding="utf-8",
    )
    (tmp_path / "output_channel_day").write_text(
        "yr mon day flo_out\n"
        "yyyy mm dd m3/day\n"
        "2020 1 1 172800\n",
        encoding="utf-8",
    )
    parsed = SwatOutputParser().parse(tmp_path)
    assert parsed.records == [{
        "period": "2020-01-01", "runoff_mm": 2.5, "evapotranspiration_mm": 3.0,
        "percolation_mm": 4.0, "soil_water_mm": 180.0, "streamflow_m3s": 2.0,
    }]
    assert parsed.water_balance["variable_availability"]["streamflow_m3s"] == "AVAILABLE"


def test_parser_accepts_singleton_basin_unit_with_explicit_channel_outlet(tmp_path: Path):
    (tmp_path / "basin_wb_day.txt").write_text(
        "yr mon day unit surq et perc sw\n"
        "yyyy mm dd --- mm mm mm mm\n"
        "2020 1 1 1 2.5 3.0 4.0 180\n",
        encoding="utf-8",
    )
    (tmp_path / "channel_sd_day.txt").write_text(
        "yr mon day unit gis_id flo_out\n"
        "yyyy mm dd --- --- m3/s\n"
        "2020 1 1 25 10 1.0\n"
        "2020 1 1 25 153 2.0\n",
        encoding="utf-8",
    )
    parsed = SwatOutputParser(outlet_unit="153").parse(tmp_path)
    assert parsed.records == [{
        "period": "2020-01-01", "runoff_mm": 2.5, "evapotranspiration_mm": 3.0,
        "percolation_mm": 4.0, "soil_water_mm": 180.0, "streamflow_m3s": 2.0,
    }]


def test_success_without_output_is_not_reported_as_success(tmp_path: Path):
    config = _config(tmp_path, _project(tmp_path), _executable(tmp_path))
    with pytest.raises(SwatOutputNotFoundError) as raised:
        SwatPlusAdapter().run(config)
    assert raised.value.code == "SWAT_OUTPUT_NOT_FOUND"


def test_nonzero_process_exit_is_not_reported_as_success(tmp_path: Path):
    config = _config(tmp_path, _project(tmp_path), _executable(tmp_path, "echo failed >&2\nexit 7"))
    with pytest.raises(SwatRunFailedError) as raised:
        SwatPlusAdapter().run(config)
    assert raised.value.code == "SWAT_RUN_FAILED"
    assert raised.value.details["exit_code"] == 7


def test_adapter_uses_isolated_workspace_and_parses_real_process_output(tmp_path: Path):
    project = _project(tmp_path)
    (project / "basin_wb_day.txt").write_text("stale source result\n", encoding="utf-8")
    executable = _executable(tmp_path, "printf 'yr mon day surq et perc sw\\nyyyy mm dd mm mm mm mm\\n2020 1 1 1 2 3 150\\n' > output_wb_day\nprintf 'yr mon day flo_out\\nyyyy mm dd m3/s\\n2020 1 1 4\\n' > output_channel_day")
    config = _config(tmp_path, project, executable)
    result = SwatPlusAdapter().run(config)
    assert result.status == "COMPLETED"
    assert result.provenance["evidence_type"] == "REAL_SWAT_PLUS"
    assert result.records[0]["streamflow_m3s"] == 4.0
    assert not (project / "output_wb_day").exists()
    assert (project / "basin_wb_day.txt").read_text(encoding="utf-8") == "stale source result\n"
    assert (Path(result.workspace) / "output_wb_day").is_file()
    assert "basin_wb_day.txt" in result.provenance["stale_workspace_outputs_removed"]
    assert result.provenance["configured_control_files"]["time_sim"]["yrc_start"] == 2020
    assert result.provenance["configured_control_files"]["print_prt"]["frequency"] == "DAILY"


def test_adapter_records_only_the_coupled_input_checksum_delta(tmp_path: Path):
    project = _project(tmp_path)
    (project / "plants.plt").write_text("plants\nname lai_pot\ncorn 6\n", encoding="utf-8")
    source_plants_checksum = hashlib.sha256((project / "plants.plt").read_bytes()).hexdigest()
    executable = _executable(tmp_path, "printf 'yr mon day surq et perc sw\\nyyyy mm dd mm mm mm mm\\n2020 1 1 1 2 3 150\\n2020 1 2 1 2 3 150\\n' > output_wb_day\nprintf 'yr mon day flo_out\\nyyyy mm dd m3/s\\n2020 1 1 4\\n2020 1 2 4\\n' > output_channel_day")
    def mutator(workspace: Path):
        (workspace / "plants.plt").write_text("plants\nname lai_pot\ncorn 5\n", encoding="utf-8")
        return {"status": "APPLIED", "workspace_input_files_modified": ["plants.plt"]}
    result = SwatPlusAdapter().run(
        _config(tmp_path, project, executable),
        workspace_mutator=mutator,
    )
    assert result.provenance["input_checksum_diff"]["changed"] == ["plants.plt"]
    assert result.provenance["input_checksums_before_mutator"]["plants.plt"] != result.provenance["input_checksums_after_mutator"]["plants.plt"]
    assert hashlib.sha256((project / "plants.plt").read_bytes()).hexdigest() == source_plants_checksum


@pytest.mark.asyncio
async def test_engine_persists_a_real_swat_adapter_result(tmp_path: Path):
    project = _project(tmp_path)
    executable = _executable(tmp_path, "printf 'yr mon day surq et perc sw\\nyyyy mm dd mm mm mm mm\\n2020 1 1 1 2 3 150\\n2020 1 2 2 3 4 151\\n' > output_wb_day\nprintf 'yr mon day flo_out\\nyyyy mm dd m3/s\\n2020 1 1 4\\n2020 1 2 5\\n' > output_channel_day")
    async with AsyncSessionLocal() as db:
        user_id = await db.scalar(select(User.id).limit(1))
        watershed_id = await db.scalar(select(Watershed.id).limit(1))
        scenario_id = await db.scalar(select(ClimateScenario.id).limit(1))
        run = SimulationRun(
            user_id=user_id, watershed_id=watershed_id, scenario_id=scenario_id,
            name="Real SWAT adapter fixture", duration_days=2, seed=42, parameters={},
            mode="SWAT_PLUS", hydrology_backend="SWAT_PLUS", start_date=date(2020, 1, 1), end_date=date(2020, 1, 2),
            requested_config={"swat_plus": {"project_path": str(project), "executable_path": str(executable),
                              "working_directory": str(tmp_path / "runs"), "output_frequency": "DAILY"}},
        )
        db.add(run)
        await db.commit()
        completed = await TwinCouplingEngine.execute_simulation_run(db, run.id)
        assert completed.status == "COMPLETED"
        assert completed.provenance["evidence_type"] == "REAL_SWAT_PLUS"
        assert completed.monthly_outputs[1]["streamflow_m3s"] == 5.0
        assert completed.summary_metrics["total_runoff_mm"] == 3.0


@pytest.mark.integration
@pytest.mark.asyncio
async def test_real_swat_baseline_api_when_locally_configured():
    executable = os.getenv("SWAT_PLUS_EXECUTABLE")
    project = os.getenv("SWAT_PLUS_PROJECT_DIR")
    start = os.getenv("SWAT_PLUS_INTEGRATION_START")
    end = os.getenv("SWAT_PLUS_INTEGRATION_END")
    if not executable or not project or not Path(executable).is_file() or not Path(project).is_dir() or not start or not end:
        pytest.skip("SKIPPED_SWAT_NOT_INSTALLED")
    source_time_sim = Path(project) / "time.sim"
    if not source_time_sim.is_file():
        source_time_sim = Path(project) / "TxtInOut" / "time.sim"
    source_checksum_before = hashlib.sha256(source_time_sim.read_bytes()).hexdigest()
    requested_start, requested_end = date.fromisoformat(start), date.fromisoformat(end)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        login = await client.post("/api/v1/auth/login", json={
            "email": "investigador@digitaltwin.org", "password": "Investiga123!",
        })
        headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
        watershed = (await client.get("/api/v1/simulations/watersheds/all", headers=headers)).json()[0]
        scenario = (await client.get("/api/v1/simulations/scenarios/all", headers=headers)).json()[0]
        response = await client.post("/api/v1/simulations", headers=headers, json={
            "name": "SWAT+ real integration", "watershed_id": watershed["id"], "scenario_id": scenario["id"],
            "duration_days": (requested_end - requested_start).days + 1,
            "start_date": start, "end_date": end, "mode": "SWAT_PLUS", "hydrology_backend": "SWAT_PLUS",
            "swat_plus": {"project_path": project, "executable_path": executable,
                          "working_directory": os.getenv("SWAT_PLUS_WORKING_DIRECTORY", ".pytest-swat-runs"),
                          "warmup_period": int(os.getenv("SWAT_PLUS_INTEGRATION_WARMUP", "0")),
                          "output_frequency": os.getenv("SWAT_PLUS_INTEGRATION_OUTPUT_FREQUENCY", "DAILY"),
                          "timeout_seconds": int(os.getenv("SWAT_PLUS_TIMEOUT_SECONDS", "3600"))},
        })
        assert response.status_code == 201, response.text
        run = response.json()
        assert run["status"] == "COMPLETED"
        assert run["provenance"]["evidence_type"] == "REAL_SWAT_PLUS"
        assert run["provenance"]["exit_code"] == 0
        assert run["provenance"]["output_generation"]
        assert all(item["generated_after_start"] for item in run["provenance"]["output_generation"].values())
        outputs = await client.get(f"/api/v1/simulations/{run['id']}/swat-results", headers=headers)
        assert outputs.status_code == 200
        assert outputs.json()["records"]
    assert hashlib.sha256(source_time_sim.read_bytes()).hexdigest() == source_checksum_before


@pytest.mark.integration
@pytest.mark.asyncio
async def test_real_fspm_to_hru_to_swat_plus_coupled_pair_when_locally_configured():
    """No fixture outputs: exercise the full persisted paired real-SWAT+ path."""
    executable = os.getenv("SWAT_PLUS_EXECUTABLE")
    project = os.getenv("SWAT_PLUS_COUPLED_PROJECT")
    start, end = os.getenv("SWAT_PLUS_COUPLED_START"), os.getenv("SWAT_PLUS_COUPLED_END")
    if not executable or not project or not start or not end:
        pytest.skip("SKIPPED_COUPLED_SWAT_NOT_CONFIGURED")
    requested_start, requested_end = date.fromisoformat(start), date.fromisoformat(end)
    source_plants = Path(project) / "plants.plt"
    checksum_before = hashlib.sha256(source_plants.read_bytes()).hexdigest()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        login = await client.post("/api/v1/auth/login", json={"email": "investigador@digitaltwin.org", "password": "Investiga123!"})
        headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
        watershed = (await client.get("/api/v1/simulations/watersheds/all", headers=headers)).json()[0]
        scenario = (await client.get("/api/v1/simulations/scenarios/all", headers=headers)).json()[0]
        response = await client.post("/api/v1/simulations", headers=headers, json={
            "name": "Real paired FSPM/SWAT+ integration", "watershed_id": watershed["id"], "scenario_id": scenario["id"],
            "duration_days": (requested_end - requested_start).days + 1, "start_date": start, "end_date": end,
            "seed": 42, "plant_count": 1000, "mode": "SWAT_PLUS", "hydrology_backend": "SWAT_PLUS",
            "swat_plus": {"project_path": project, "executable_path": executable,
                          "working_directory": os.getenv("SWAT_PLUS_COUPLED_WORKDIR", ".pytest-coupled-swat-runs"),
                          "output_frequency": "DAILY", "timeout_seconds": 300,
                          "run_type": "SWAT_MULTISCALE_COUPLED", "target_plant_name": "corn"},
        })
        assert response.status_code == 201, response.text
        coupled = response.json()
        assert coupled["provenance"]["evidence_type"] == "REAL_SWAT_PLUS_COUPLED"
        updates = coupled["provenance"]["parameter_updates"]
        assert updates and all(item["original_value"] != item["coupled_value"] for item in updates)
        comparison = coupled["summary_metrics"]["paired_comparison"]
        assert comparison["baseline_run_id"] and comparison["coupled_run_id"] == coupled["id"]
        assert comparison["evapotranspiration_mm"]["delta_absolute"] is not None
        assert coupled["provenance"]["date_of_peak_LAI"]
        assert coupled["provenance"]["date_of_peak_height"]
        assert coupled["provenance"]["date_of_peak_root_depth"]
        results = await client.get(f"/api/v1/simulations/{coupled['id']}/swat-results", headers=headers)
        assert results.status_code == 200 and results.json()["records"]
        baseline = await client.get(f"/api/v1/simulations/{comparison['baseline_run_id']}", headers=headers)
        assert baseline.status_code == 200
        baseline_payload = baseline.json()
        assert baseline_payload["provenance"]["evidence_type"] == "REAL_SWAT_PLUS"
        assert baseline_payload["provenance"]["exit_code"] == 0
        assert all(item["generated_after_start"] for item in baseline_payload["provenance"]["output_generation"].values())
        baseline_results = await client.get(f"/api/v1/simulations/{comparison['baseline_run_id']}/swat-results", headers=headers)
        assert baseline_results.status_code == 200 and baseline_results.json()["records"]
        baseline_plants = Path(baseline_payload["provenance"]["workspace"]) / "plants.plt"
        coupled_plants = Path(coupled["provenance"]["workspace"]) / "plants.plt"
        assert hashlib.sha256(baseline_plants.read_bytes()).hexdigest() != hashlib.sha256(coupled_plants.read_bytes()).hexdigest()
    assert hashlib.sha256(source_plants.read_bytes()).hexdigest() == checksum_before
