from datetime import date
import os
from pathlib import Path

import pytest
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
    SwatProjectNotFoundError,
    SwatRunFailedError,
)
from app.services.swat_plus_parser import SwatOutputParser
from app.services.twin_coupling_engine import TwinCouplingEngine


def _project(tmp_path: Path) -> Path:
    project = tmp_path / "source-project"
    project.mkdir()
    (project / "file.cio").write_text("SWAT+ input fixture\n", encoding="utf-8")
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
    executable = _executable(tmp_path, "printf 'yr mon day surq et perc sw\\nyyyy mm dd mm mm mm mm\\n2020 1 1 1 2 3 150\\n' > output_wb_day\nprintf 'yr mon day flo_out\\nyyyy mm dd m3/s\\n2020 1 1 4\\n' > output_channel_day")
    config = _config(tmp_path, project, executable)
    result = SwatPlusAdapter().run(config)
    assert result.status == "COMPLETED"
    assert result.provenance["evidence_type"] == "REAL_SWAT_PLUS"
    assert result.records[0]["streamflow_m3s"] == 4.0
    assert not (project / "output_wb_day").exists()
    assert (Path(result.workspace) / "output_wb_day").is_file()


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
def test_real_swat_baseline_when_locally_configured():
    executable = os.getenv("SWAT_PLUS_EXECUTABLE")
    project = os.getenv("SWAT_PLUS_PROJECT_DIR")
    start = os.getenv("SWAT_PLUS_INTEGRATION_START")
    end = os.getenv("SWAT_PLUS_INTEGRATION_END")
    if not executable or not project or not Path(executable).is_file() or not Path(project).is_dir() or not start or not end:
        pytest.skip("SKIPPED_SWAT_NOT_INSTALLED")
    config = SwatPlusRunConfig(
        project_path=Path(project), executable_path=Path(executable),
        working_directory=Path(os.getenv("SWAT_PLUS_WORKING_DIRECTORY", ".pytest-swat-runs")),
        simulation_start=date.fromisoformat(start), simulation_end=date.fromisoformat(end),
        warmup_period=int(os.getenv("SWAT_PLUS_INTEGRATION_WARMUP", "0")),
        output_frequency=os.getenv("SWAT_PLUS_INTEGRATION_OUTPUT_FREQUENCY", "DAILY"),
        watershed_id=os.getenv("SWAT_PLUS_INTEGRATION_WATERSHED", "configured-watershed"),
        run_id=f"pytest-real-{os.getpid()}", timeout_seconds=int(os.getenv("SWAT_PLUS_TIMEOUT_SECONDS", "3600")),
    )
    result = SwatPlusAdapter().run(config)
    assert result.status == "COMPLETED"
    assert result.provenance["evidence_type"] == "REAL_SWAT_PLUS"
    assert result.records
