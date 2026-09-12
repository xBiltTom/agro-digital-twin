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
from typing import Any

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
        if self.run_type != "SWAT_STANDARD_BASELINE":
            raise SwatProjectInvalidError("Only SWAT_STANDARD_BASELINE is supported in this phase")
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

    def run(self, config: SwatPlusRunConfig | None = None, timeout_seconds: int | None = None) -> SwatRunResult:
        """Execute exactly one baseline run. The original project is never modified."""
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
        # A project template can contain old results. Remove only recognized output
        # files from the newly created workspace so they cannot be misreported as
        # results from this execution.
        for stale_output in run_directory.glob("output_*"):
            if stale_output.is_file():
                stale_output.unlink()
        command = [str(config.executable_path.resolve())]
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

        return SwatRunResult(
            status="COMPLETED", run_id=config.run_id, watershed_id=config.watershed_id,
            start_date=config.simulation_start.isoformat(), end_date=config.simulation_end.isoformat(),
            workspace=str(workspace), exit_code=completed.returncode, duration_seconds=duration,
            stdout=completed.stdout, stderr=completed.stderr, records=parsed.records, hru_results=parsed.hru_results,
            water_balance=parsed.water_balance, output_files=parsed.output_files,
            provenance={
                "evidence_type": "REAL_SWAT_PLUS", "engine": "SWAT+", "command": command,
                "executable_path": str(config.executable_path.resolve()), "executable_sha256": _sha256(config.executable_path),
                "executable_version": self._version_from_stdout(completed.stdout), "source_project": str(source_root),
                "source_file_cio_sha256": _sha256(input_directory / "file.cio"), "workspace": str(workspace),
                "output_checksums": {str(path.relative_to(workspace)): _sha256(path) for path in parsed.source_files},
                "output_frequency": config.output_frequency, "warmup_period": config.warmup_period,
            },
        )
