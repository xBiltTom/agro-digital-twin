"""Isolated, reproducible execution adapter for a real SWAT+ installation.

This module deliberately has no hydrological fallback. A missing binary, invalid
project, failed process, or missing output is always represented by a typed error.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date
import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import time
from typing import Any, Callable

from app.services.swat_plus_parser import SwatOutputParser, SwatParsedOutput


class SwatPlusError(RuntimeError):
    """Base error whose stable code is safe to expose through the API."""

    code = "SWAT_RUN_FAILED"

    def __init__(self, message: str, *, details: dict[str, Any] | None = None):
        super().__init__(message)
        self.details = details or {}


class SwatExecutableNotFoundError(SwatPlusError):
    code = "SWAT_EXECUTABLE_NOT_FOUND"


class SwatProjectNotFoundError(SwatPlusError):
    code = "SWAT_PROJECT_NOT_FOUND"


class SwatProjectInvalidError(SwatPlusError):
    code = "SWAT_PROJECT_INVALID"


class SwatRunFailedError(SwatPlusError):
    code = "SWAT_RUN_FAILED"


class SwatOutputNotFoundError(SwatPlusError):
    code = "SWAT_OUTPUT_NOT_FOUND"


class SwatOutputParseError(SwatPlusError):
    code = "SWAT_OUTPUT_PARSE_ERROR"


@dataclass(frozen=True)
class SwatPlusRunConfig:
    project_path: Path
    executable_path: Path
    working_directory: Path
    simulation_start: date
    simulation_end: date
    warmup_period: int
    output_frequency: str
    watershed_id: str
    run_id: str
    timeout_seconds: int = 3600
    run_type: str = "SWAT_STANDARD_BASELINE"
    outlet_unit: str | None = None

    def validate(self) -> None:
        if self.run_type not in {"SWAT_STANDARD_BASELINE", "SWAT_MULTISCALE_COUPLED"}:
            raise SwatProjectInvalidError("run_type must be SWAT_STANDARD_BASELINE or SWAT_MULTISCALE_COUPLED")
        if self.simulation_end < self.simulation_start:
            raise SwatProjectInvalidError("simulation_end must not precede simulation_start")
        if self.warmup_period < 0:
            raise SwatProjectInvalidError("warmup_period must be zero or greater")
        if self.output_frequency not in {"DAILY", "MONTHLY", "ANNUAL"}:
            raise SwatProjectInvalidError("output_frequency must be DAILY, MONTHLY, or ANNUAL")
        if not self.run_id or not self.watershed_id:
            raise SwatProjectInvalidError("run_id and watershed_id are required")
        if self.timeout_seconds <= 0:
            raise SwatProjectInvalidError("timeout_seconds must be positive")


@dataclass(frozen=True)
class SwatRunResult:
    status: str
    run_id: str
    watershed_id: str
    start_date: str
    end_date: str
    workspace: str
    exit_code: int
    duration_seconds: float
    stdout: str
    stderr: str
    records: list[dict[str, Any]]
    hru_results: list[dict[str, Any]]
    water_balance: dict[str, Any]
    output_files: list[str]
    provenance: dict[str, Any]

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


_RECOGNIZED_OUTPUT_PATTERNS = (
    "output_wb*", "basin_wb*", "output_channel*", "channel_sd*", "output_hru*", "hru_wb*",
)


def _day_of_year(value: date) -> int:
    return value.timetuple().tm_yday


def _replace_control_values(path: Path, values: str, *, label: str) -> None:
    """Replace the first list-directed numeric record after the two-line header."""
    lines = path.read_text(encoding="utf-8", errors="strict").splitlines()
    if len(lines) < 3:
        raise SwatProjectInvalidError(f"{label} is too short to configure", details={"path": str(path)})
    lines[2] = values
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _configure_time_sim(path: Path, config: SwatPlusRunConfig) -> dict[str, Any]:
    values = f"{_day_of_year(config.simulation_start):8d} {config.simulation_start.year:9d} {_day_of_year(config.simulation_end):8d} {config.simulation_end.year:9d} {0:9d}"
    _replace_control_values(path, values, label="time.sim")
    return {
        "path": str(path), "sha256": _sha256(path), "day_start": _day_of_year(config.simulation_start),
        "yrc_start": config.simulation_start.year, "day_end": _day_of_year(config.simulation_end),
        "yrc_end": config.simulation_end.year, "step": 0,
    }


def _configure_print_prt(path: Path, config: SwatPlusRunConfig) -> dict[str, Any]:
    """Set SWAT+ print window and requested object frequency in a real print.prt."""
    lines = path.read_text(encoding="utf-8", errors="strict").splitlines()
    if len(lines) < 10:
        raise SwatProjectInvalidError("print.prt is too short to configure", details={"path": str(path)})
    lines[2] = (
        f"{config.warmup_period:8d} {_day_of_year(config.simulation_start):10d} {config.simulation_start.year:10d} "
        f"{_day_of_year(config.simulation_end):8d} {config.simulation_end.year:9d} {1:10d}"
    )
    flag_index = {"DAILY": 1, "MONTHLY": 2, "ANNUAL": 3}[config.output_frequency]
    configured_objects: list[str] = []
    # These are real SWAT+ object labels. Keep AVANN disabled: the API asks for a
    # period-specific baseline, and the parser consumes the selected frequency.
    desired = {"basin_wb", "hru_wb", "channel", "channel_sd"}
    for index, line in enumerate(lines):
        tokens = line.split()
        # Official editor projects often enable unrelated daily diagnostics.
        # Disable them only in the copied workspace; selected parser objects are
        # enabled below, so the hydrology and source project are unchanged.
        if len(tokens) >= 5 and all(flag.lower() in {"y", "n", "l", "b"} for flag in tokens[1:5]):
            lines[index] = f"{tokens[0]:<24}{'n':>8}{'n':>14}{'n':>14}{'n':>14}"
        if len(tokens) >= 5 and tokens[0] in desired:
            flags = ["n", "n", "n", "n"]
            flags[flag_index - 1] = "y"
            lines[index] = f"{tokens[0]:<24}{flags[0]:>8}{flags[1]:>14}{flags[2]:>14}{flags[3]:>14}"
            configured_objects.append(tokens[0])
    if "basin_wb" not in configured_objects:
        # ``basin_wb`` is a real SWAT+ print object. Some official reference
        # projects ship it only as an avann artifact and omit it from print.prt;
        # append an explicit row so the requested period has a watershed output.
        flags = ["n", "n", "n", "n"]
        flags[flag_index - 1] = "y"
        lines.append(f"{'basin_wb':<24}{flags[0]:>8}{flags[1]:>14}{flags[2]:>14}{flags[3]:>14}")
        configured_objects.append("basin_wb")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {
        "path": str(path), "sha256": _sha256(path), "nyskip": config.warmup_period,
        "day_start": _day_of_year(config.simulation_start), "yrc_start": config.simulation_start.year,
        "day_end": _day_of_year(config.simulation_end), "yrc_end": config.simulation_end.year,
        "interval": 1, "frequency": config.output_frequency, "objects": configured_objects,
    }


class SwatPlusAdapter:
    """Runs SWAT+ in a copy of a source project and parses only its real outputs."""

    def __init__(self, executable: str | Path | None = None, project_dir: str | Path | None = None,
                 working_directory: str | Path | None = None):
        self.executable = Path(executable or os.getenv("SWAT_PLUS_EXECUTABLE", ""))
        self.project_dir = Path(project_dir or os.getenv("SWAT_PLUS_PROJECT_DIR", ""))
        self.working_directory = Path(working_directory or os.getenv("SWAT_PLUS_WORKING_DIRECTORY", ""))

    @staticmethod
    def _input_directory(project_path: Path) -> Path:
        if (project_path / "file.cio").is_file():
            return project_path
        if (project_path / "TxtInOut" / "file.cio").is_file():
            return project_path / "TxtInOut"
        raise SwatProjectInvalidError(
            "SWAT+ project does not contain required file.cio (at project root or TxtInOut)",
            details={"project_path": str(project_path)},
        )

    @staticmethod
    def _clear_recognized_outputs(run_directory: Path) -> dict[str, str]:
        """Delete stale parser inputs only from the newly copied workspace."""
        stale: dict[str, str] = {}
        for pattern in _RECOGNIZED_OUTPUT_PATTERNS:
            for output in run_directory.glob(pattern):
                if output.is_file():
                    stale[str(output.relative_to(run_directory))] = _sha256(output)
                    output.unlink()
        return stale

    @staticmethod
    def _validate_resources(config: SwatPlusRunConfig) -> Path:
        config.validate()
        if not config.executable_path.is_file():
            raise SwatExecutableNotFoundError("SWAT+ executable was not found", details={"path": str(config.executable_path)})
        if not os.access(config.executable_path, os.X_OK):
            raise SwatExecutableNotFoundError("SWAT+ executable is not executable", details={"path": str(config.executable_path)})
        if not config.project_path.is_dir():
            raise SwatProjectNotFoundError("SWAT+ project directory was not found", details={"path": str(config.project_path)})
        return SwatPlusAdapter._input_directory(config.project_path)

    def capability(self) -> dict[str, Any]:
        try:
            if not self.executable.is_file() or not self.project_dir.is_dir():
                raise SwatExecutableNotFoundError("executable/project not configured")
            input_directory = self._input_directory(self.project_dir)
            active = os.access(self.executable, os.X_OK)
            return {
                "status": "ACTIVE" if active else "NOT_AVAILABLE",
                "executable": str(self.executable), "project_dir": str(self.project_dir),
                "input_directory": str(input_directory),
                "reason": None if active else "executable is not executable",
            }
        except SwatPlusError as exc:
            return {"status": "NOT_AVAILABLE", "executable": str(self.executable),
                    "project_dir": str(self.project_dir), "reason": f"{exc.code}: {exc}"}

    @staticmethod
    def _version_from_stdout(stdout: str) -> str | None:
        """Extract a banner when available without ever invoking SWAT+ twice."""
        for line in stdout.splitlines():
            if "swat" in line.lower() and "version" in line.lower():
                return line.strip()[:500]
        return None

    @classmethod
    def _version_from_run(cls, stdout: str, run_directory: Path) -> str | None:
        """Use the normal run banner when SWAT+ writes it to simulation.out."""
        version = cls._version_from_stdout(stdout)
        if version:
            return version
        simulation_output = run_directory / "simulation.out"
        if not simulation_output.is_file():
            return None
        text = simulation_output.read_text(encoding="utf-8", errors="replace")[:4000]
        revision = next((line.strip() for line in text.splitlines() if "revision" in line.lower()), None)
        return revision[:500] if revision else None

    def run(self, config: SwatPlusRunConfig | None = None, timeout_seconds: int | None = None,
            workspace_mutator: Callable[[Path], dict[str, Any]] | None = None) -> SwatRunResult:
        """Execute one real run; an optional mutator may edit only its copied inputs."""
        if config is None:
            # Compatibility only; normal application calls always provide the
            # explicit contract built by TwinCouplingEngine.
            config = SwatPlusRunConfig(
                project_path=self.project_dir, executable_path=self.executable,
                working_directory=self.working_directory or (self.project_dir.parent / "swat-runs"),
                simulation_start=date.today(), simulation_end=date.today(), warmup_period=0,
                output_frequency="DAILY", watershed_id="unspecified", run_id=f"manual-{int(time.time())}",
                timeout_seconds=timeout_seconds or 3600,
            )
        input_directory = self._validate_resources(config)
        source_root = config.project_path.resolve()
        workspace_root = config.working_directory.resolve()
        workspace_root.mkdir(parents=True, exist_ok=True)
        if not os.access(workspace_root, os.W_OK):
            raise SwatProjectInvalidError("SWAT+ working directory is not writable", details={"path": str(workspace_root)})
        workspace = workspace_root / config.run_id
        if workspace.exists():
            raise SwatProjectInvalidError("SWAT+ workspace already exists for this run_id", details={"workspace": str(workspace)})

        started = time.monotonic()
        try:
            shutil.copytree(source_root, workspace)
        except OSError as exc:
            raise SwatProjectInvalidError("Unable to create isolated SWAT+ workspace", details={"workspace": str(workspace)}) from exc
        run_directory = workspace / input_directory.relative_to(source_root)
        # Inputs are configured only after the copy. The source project remains
        # read-only and can therefore be reused for independent runs.
        time_sim = run_directory / "time.sim"
        print_prt = run_directory / "print.prt"
        if not time_sim.is_file() or not print_prt.is_file():
            raise SwatProjectInvalidError("SWAT+ project must include time.sim and print.prt", details={"workspace": str(workspace)})
        control_files = {
            "time_sim": _configure_time_sim(time_sim, config),
            "print_prt": _configure_print_prt(print_prt, config),
        }
        stale_outputs = self._clear_recognized_outputs(run_directory)
        workspace_modifications: dict[str, Any] = {"status": "NOT_APPLIED"}
        if workspace_mutator is not None:
            try:
                workspace_modifications = workspace_mutator(run_directory)
            except Exception as exc:
                raise SwatProjectInvalidError("Coupled SWAT+ input preparation failed", details={"workspace": str(workspace), "message": str(exc)}) from exc
        command = [str(config.executable_path.resolve())]
        execution_started_ns = time.time_ns()
        try:
            completed = subprocess.run(command, cwd=run_directory, capture_output=True, text=True,
                                       timeout=config.timeout_seconds, check=False)
        except subprocess.TimeoutExpired as exc:
            duration = time.monotonic() - started
            raise SwatRunFailedError("SWAT+ process timed out", details={
                "timeout_seconds": config.timeout_seconds, "duration_seconds": duration,
                "stdout": (exc.stdout or "")[-4000:], "stderr": (exc.stderr or "")[-4000:],
                "workspace": str(workspace),
            }) from exc
        except OSError as exc:
            raise SwatRunFailedError("Unable to start SWAT+ executable", details={"workspace": str(workspace)}) from exc
        duration = time.monotonic() - started
        if completed.returncode != 0:
            raise SwatRunFailedError("SWAT+ process exited with a non-zero status", details={
                "exit_code": completed.returncode, "stdout": completed.stdout[-4000:], "stderr": completed.stderr[-4000:],
                "duration_seconds": duration, "workspace": str(workspace), "command": command,
            })

        try:
            parsed: SwatParsedOutput = SwatOutputParser(
                output_frequency=config.output_frequency, outlet_unit=config.outlet_unit,
            ).parse(
                run_directory, start_date=config.simulation_start, end_date=config.simulation_end,
            )
        except FileNotFoundError as exc:
            raise SwatOutputNotFoundError("SWAT+ completed but did not generate a recognized hydrological output", details={
                "workspace": str(workspace), "expected": "output_wb* and/or output_channel*",
            }) from exc
        except ValueError as exc:
            raise SwatOutputParseError("SWAT+ output could not be parsed", details={"workspace": str(workspace)}) from exc
        output_generation = {
            str(path.relative_to(workspace)): {"sha256": _sha256(path), "mtime_ns": path.stat().st_mtime_ns,
                                                "generated_after_start": path.stat().st_mtime_ns >= execution_started_ns}
            for path in parsed.source_files
        }
        if not all(item["generated_after_start"] for item in output_generation.values()):
            raise SwatOutputParseError("Parsed SWAT+ output predates this execution", details={"workspace": str(workspace)})

        return SwatRunResult(
            status="COMPLETED", run_id=config.run_id, watershed_id=config.watershed_id,
            start_date=config.simulation_start.isoformat(), end_date=config.simulation_end.isoformat(),
            workspace=str(workspace), exit_code=completed.returncode, duration_seconds=duration,
            stdout=completed.stdout, stderr=completed.stderr, records=parsed.records, hru_results=parsed.hru_results,
            water_balance=parsed.water_balance, output_files=parsed.output_files,
            provenance={
                "evidence_type": "REAL_SWAT_PLUS", "engine": "SWAT+", "command": command,
                "executable_path": str(config.executable_path.resolve()), "executable_sha256": _sha256(config.executable_path),
                "executable_version": self._version_from_run(completed.stdout, run_directory), "source_project": str(source_root),
                "source_file_cio_sha256": _sha256(input_directory / "file.cio"), "workspace": str(workspace),
                "output_checksums": {str(path.relative_to(workspace)): _sha256(path) for path in parsed.source_files},
                "stale_workspace_outputs_removed": stale_outputs, "configured_control_files": control_files,
                "workspace_modifications": workspace_modifications,
                "output_generation": output_generation,
                "output_frequency": config.output_frequency, "warmup_period": config.warmup_period,
            },
        )
