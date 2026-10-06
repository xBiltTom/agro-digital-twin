"""Isolated, reproducible execution adapter for a real SWAT+ installation.

This module deliberately has no hydrological fallback. A missing binary, invalid
project, failed process, or missing output is always represented by a typed error.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from datetime import date
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import time
from typing import Any, Callable

from app.services.swat_plus_parser import SwatOutputParser, SwatParsedOutput
from app.services.swat_input_compatibility import (
    SwatInputCompatibility,
    SwatInputCompatibilityError,
)


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


class SwatCoupledPreflightBlockedError(SwatPlusError):
    code = "SWAT_COUPLED_PREFLIGHT_BLOCKED"


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


def swat_run_config_from_request(
    requested: dict[str, Any], *, simulation_start: date, simulation_end: date,
    watershed_id: str, run_id: str, run_type: str | None = None,
    outlet_unit: str | None = None,
) -> SwatPlusRunConfig:
    """Build one SWAT contract consistently for preflight and execution."""
    from app.core.config import settings

    return SwatPlusRunConfig(
        project_path=Path(requested.get("project_path") or settings.SWAT_PLUS_PROJECT_DIR),
        executable_path=Path(requested.get("executable_path") or settings.SWAT_PLUS_EXECUTABLE),
        working_directory=Path(requested.get("working_directory") or settings.SWAT_PLUS_WORKING_DIRECTORY),
        simulation_start=simulation_start,
        simulation_end=simulation_end,
        warmup_period=requested.get("warmup_period", 0),
        output_frequency=requested.get("output_frequency", "DAILY"),
        watershed_id=watershed_id,
        run_id=run_id,
        timeout_seconds=requested.get("timeout_seconds", settings.SWAT_PLUS_TIMEOUT_SECONDS),
        run_type=run_type or requested.get("run_type", "SWAT_STANDARD_BASELINE"),
        outlet_unit=requested.get("outlet_unit") or outlet_unit
        or ("153" if "05451210" in watershed_id else None),
    )


def require_coupled_preflight_ready(preflight: dict[str, Any]) -> None:
    """Stop before running SWAT+ when the exact crop/forcing contract is blocked."""
    if preflight.get("status") != "READY":
        raise SwatCoupledPreflightBlockedError(
            "SWAT+ coupled run failed its pre-execution scientific preflight",
            details={
                "preflight": preflight,
                "blockers": preflight.get("blockers", []),
            },
        )


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
    plant_results: list[dict[str, Any]]
    channel_results: list[dict[str, Any]]
    management_events: list[dict[str, Any]]
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
    "output_wb*", "basin_wb*", "output_channel*", "channel_sd*", "channel_sdmorph*",
    "channel_day*", "channel_mon*", "channel_yr*", "channel_aa*", "output_hru*", "hru_wb*",
    "hru_pw*", "mgt_out*", "crop_yld*", "basin_crop_yld*", "success.fin",
    "simulation.out", "diagnostics.out", "checker.out",
    "area_calc.out", "erosion.out",
)
_TRACEABLE_INPUT_FILES = (
    "plants.plt", "plant.ini", "landuse.lum", "management.sch", "hru-data.hru",
    "soils.sol", "soil_plant.ini", "time.sim", "print.prt",
    "tiledrain.str", "hydrology.hyd", "codes.bsn", "rout_unit.con", "hru.con",
    "aquifer.con", "chandeg.con", "rout_unit.rtu", "ls_unit.def", "ls_unit.ele",
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
    run_start_year = config.simulation_start.year - config.warmup_period
    values = f"{_day_of_year(config.simulation_start):8d} {run_start_year:9d} {_day_of_year(config.simulation_end):8d} {config.simulation_end.year:9d} {0:9d}"
    _replace_control_values(path, values, label="time.sim")
    return {
        "path": str(path), "sha256": _sha256(path), "day_start": _day_of_year(config.simulation_start),
        "yrc_start": run_start_year, "day_end": _day_of_year(config.simulation_end),
        "yrc_end": config.simulation_end.year, "step": 0,
        "warmup_years": config.warmup_period,
    }


def _configure_print_prt(path: Path, config: SwatPlusRunConfig) -> dict[str, Any]:
    """Set SWAT+ print window and requested object frequency in a real print.prt."""
    lines = path.read_text(encoding="utf-8", errors="strict").splitlines()
    if len(lines) < 10:
        raise SwatProjectInvalidError("print.prt is too short to configure", details={"path": str(path)})
    run_start_year = config.simulation_start.year - config.warmup_period
    lines[2] = (
        f"{config.warmup_period:8d} {_day_of_year(config.simulation_start):10d} {run_start_year:10d} "
        f"{_day_of_year(config.simulation_end):8d} {config.simulation_end.year:9d} {1:10d}"
    )
    flag_index = {"DAILY": 1, "MONTHLY": 2, "ANNUAL": 3}[config.output_frequency]
    configured_objects: list[str] = []
    # These are real SWAT+ object labels. Keep AVANN disabled: the API asks for a
    # period-specific baseline, and the parser consumes the selected frequency.
    desired = {"basin_wb", "hru_wb", "hru_pw", "channel", "channel_sd"}
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
    # Management output is a separate switch from the object frequency table.
    # It is the only direct event trace for automatic PLANT and HARV/KILL
    # operations in this project.
    for index, line in enumerate(lines[:-1]):
        if "crop_yld" in line.split() and "mgtout" in line.split():
            value_line = lines[index + 1]
            spans = list(re.finditer(r"\S+", value_line))
            if len(spans) >= 2:
                token = spans[1]
                lines[index + 1] = value_line[:token.start()] + "y" + value_line[token.end():]
            break
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {
        "path": str(path), "sha256": _sha256(path), "nyskip": config.warmup_period,
        "day_start": _day_of_year(config.simulation_start), "yrc_start": run_start_year,
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
    def _input_checksums(run_directory: Path) -> dict[str, str]:
        """Checksum the finite, named SWAT+ input contract used for lineage."""
        return {name: _sha256(run_directory / name) for name in _TRACEABLE_INPUT_FILES
                if (run_directory / name).is_file()}

    @staticmethod
    def _validate_resources(config: SwatPlusRunConfig) -> Path:
        config.validate()
        if not config.executable_path.is_file():
            raise SwatExecutableNotFoundError("SWAT+ executable was not found", details={"path": str(config.executable_path)})
        if not os.access(config.executable_path, os.X_OK):
            raise SwatExecutableNotFoundError("SWAT+ executable is not executable", details={"path": str(config.executable_path)})
        if not config.project_path.is_dir():
            raise SwatProjectNotFoundError("SWAT+ project directory was not found", details={"path": str(config.project_path)})
        input_directory = SwatPlusAdapter._input_directory(config.project_path)
        SwatPlusAdapter._validate_declared_weather_files(input_directory)
        try:
            SwatInputCompatibility.inspect(input_directory)
        except SwatInputCompatibilityError as exc:
            raise SwatProjectInvalidError(
                "SWAT+ project has an unsafe or malformed integer input field",
                details=exc.details,
            ) from exc
        return input_directory

    @staticmethod
    def _validate_declared_weather_files(input_directory: Path) -> None:
        """Reject a project whose declared local weather files are absent.

        ``weather-sta.cli`` can deliberately use ``sim`` (SWAT's weather
        generator) or ``null`` for a variable.  Those values are not files.
        Conversely, a filename in its precipitation or temperature columns is
        an input contract: running without it would either fail late inside
        SWAT+ or silently make a study non-reproducible.  Validate it before
        copying a workspace, while retaining compatibility with projects that
        do not use station weather at all.
        """
        station_file = input_directory / "weather-sta.cli"
        if not station_file.is_file():
            return
        rows = [line.split() for line in station_file.read_text(encoding="utf-8", errors="strict").splitlines()[2:]
                if line.split()]
        missing: list[str] = []
        for row in rows:
            # name, wgn, pcp, tmp, slr, hmd, wnd, pet, atmo_dep
            for value in row[2:4]:
                if value.lower() not in {"null", "sim"} and not (input_directory / value).is_file():
                    missing.append(value)
        if missing:
            raise SwatProjectInvalidError(
                "SWAT+ project declares local weather files that are missing",
                details={"input_directory": str(input_directory), "missing_weather_files": sorted(set(missing))},
            )

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

    def preflight(self, config: SwatPlusRunConfig, *, target_crop: str = "corn") -> dict[str, Any]:
        """Read-only validation of the exact requested run configuration.

        A present executable and ``file.cio`` are not enough to establish that
        a coupled run can execute. The coupled path also needs the target crop
        to be used by active HRU management and dated direct FSPM forcing.
        """
        blockers: list[dict[str, str]] = []
        checks: dict[str, Any] = {
            "executable": False,
            "project_and_declared_inputs": False,
            "control_files": False,
            "working_directory": False,
            "input_compatibility": False,
        }
        input_directory: Path | None = None
        try:
            input_directory = self._validate_resources(config)
            checks["executable"] = True
            checks["project_and_declared_inputs"] = True
            compatibility = SwatInputCompatibility.inspect(input_directory)
            checks["input_compatibility"] = True
            checks["integer_format_corrections_required_in_workspace"] = compatibility["correction_count"]
            checks["control_files"] = all((input_directory / name).is_file() for name in ("time.sim", "print.prt"))
            if not checks["control_files"]:
                blockers.append({"code": "SWAT_CONTROL_FILES_MISSING", "message": "SWAT+ input requires time.sim and print.prt"})
        except SwatPlusError as exc:
            blockers.append({"code": exc.code, "message": str(exc)})

        work_directory = config.working_directory.expanduser().resolve()
        probe = work_directory
        while not probe.exists() and probe != probe.parent:
            probe = probe.parent
        checks["working_directory"] = probe.is_dir() and os.access(probe, os.W_OK)
        if not checks["working_directory"]:
            blockers.append({"code": "SWAT_WORK_DIRECTORY_NOT_WRITABLE", "message": "SWAT+ workspace parent is not writable"})

        # A coupled run retains one calendar-discovery run and at most three
        # FSPM-parameterized calendar-convergence runs in isolated workspaces.
        estimated_executions = 4 if config.run_type == "SWAT_MULTISCALE_COUPLED" else 1
        workspace_project_copies = estimated_executions
        source_bytes = 0
        if config.project_path.is_dir():
            source_bytes = sum(path.stat().st_size for path in config.project_path.rglob("*") if path.is_file())
        free_bytes = shutil.disk_usage(probe).free if probe.is_dir() else None
        minimum_workspace_bytes = source_bytes * workspace_project_copies
        if free_bytes is not None and free_bytes < minimum_workspace_bytes:
            blockers.append({"code": "SWAT_WORKSPACE_DISK_SPACE_LOW", "message": "Free disk is below the minimum source-project copy estimate"})

        active_hru_count: int | None = None
        if config.run_type == "SWAT_MULTISCALE_COUPLED" and input_directory is not None and checks["project_and_declared_inputs"]:
            checks["coupled_crop_management"] = None
            checks["dated_fspm_forcing"] = None
            checks["executed_crop_calendar"] = "READ_FROM_MGT_OUT_AFTER_BASELINE_EXECUTION"
            active_hrus: list[str] | None = None
            forcing: list[dict[str, Any]] | None = None
            try:
                from app.services.swat_plant_parameter_mapper import SwatPlantParameterMapper

                active_hrus = SwatPlantParameterMapper._active_hrus(input_directory, target_crop)
                active_hru_count = len(active_hrus)
                checks["coupled_crop_management"] = active_hru_count > 0
            except (OSError, ValueError) as exc:
                checks["coupled_crop_management"] = False
                blockers.append({"code": "COUPLED_CROP_CONFIGURATION_INVALID", "message": str(exc)})

            try:
                from app.services.swat_plant_parameter_mapper import SwatClimateForcingReader, SwatPlantParameterMapper

                hru_file = input_directory / "hru-data.hru"
                hru_ids = {tokens[1]: int(tokens[0]) for tokens in
                           (line.split() for line in hru_file.read_text(encoding="utf-8", errors="strict").splitlines()[2:])
                           if len(tokens) >= 2 and tokens[0].isdigit()}
                selected_ids = [hru_ids[name] for name in (active_hrus or []) if name in hru_ids]
                if not selected_ids:
                    raise ValueError("Active crop HRUs cannot be mapped to numeric hru.con identifiers")
                forcing, _ = SwatClimateForcingReader(input_directory).for_hrus(
                    config.simulation_start, config.simulation_end, selected_ids, require_fspm=True
                )
                checks["dated_fspm_forcing"] = len(forcing) == (config.simulation_end - config.simulation_start).days + 1
            except (OSError, ValueError) as exc:
                checks["dated_fspm_forcing"] = False
                blockers.append({"code": "COUPLED_FSPM_FORCING_INVALID", "message": str(exc)})

        return {
            "status": "READY" if not blockers else "BLOCKED",
            "run_type": config.run_type,
            "estimated_executions": estimated_executions,
            "checks": checks,
            "blockers": blockers,
            "storage_estimate": {
                "source_project_bytes": source_bytes,
                "workspace_project_copy_count": workspace_project_copies,
                "minimum_workspace_copy_bytes": minimum_workspace_bytes,
                "free_disk_bytes": free_bytes,
                "note": "Lower bound for isolated source copies; SWAT+ output growth and runtime depend on the requested period and print frequency.",
            },
            "active_target_hru_count": active_hru_count,
            "calendar_source": "SWAT+ executed mgt_out.txt, obtained after the first real baseline run"
            if config.run_type == "SWAT_MULTISCALE_COUPLED" else None,
        }

    @staticmethod
    def _clear_recognized_outputs(run_directory: Path) -> dict[str, str]:
        """Remove stale outputs listed by SWAT+ and known output patterns.

        The list is evaluated only after copying the project into its unique
        workspace. It prevents a historical ``success.fin`` or output table
        from making a failed/current run appear complete.
        """
        stale: dict[str, str] = {}
        candidates: set[Path] = set()
        index_file = run_directory / "files_out.out"
        if index_file.is_file():
            for line in index_file.read_text(encoding="utf-8", errors="replace").splitlines()[1:]:
                tokens = line.split()
                if len(tokens) < 2:
                    continue
                relative = Path(tokens[1])
                if relative.is_absolute() or ".." in relative.parts:
                    continue
                candidate = run_directory / relative
                if candidate.is_file() and candidate.resolve().is_relative_to(run_directory.resolve()):
                    candidates.add(candidate)
        for pattern in _RECOGNIZED_OUTPUT_PATTERNS:
            candidates.update(path for path in run_directory.glob(pattern) if path.is_file())
        for output in sorted(candidates):
            if output.is_symlink():
                continue
            stale[str(output.relative_to(run_directory))] = _sha256(output)
            output.unlink()
        return stale

    @staticmethod
    def _write_failure_status(run_directory: Path, reason: str, details: dict[str, Any] | None = None) -> None:
        if run_directory.is_dir():
            payload = {"status": "FAILED", "reason": reason, "details": details or {}}
            (run_directory / "swat_run_status.json").write_text(
                json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8"
            )

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
            workspace_mutator: Callable[[Path], dict[str, Any]] | None = None,
            target_crop: str = "corn") -> SwatRunResult:
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
        if config.run_type == "SWAT_MULTISCALE_COUPLED" and workspace_mutator is None:
            require_coupled_preflight_ready(self.preflight(config, target_crop=target_crop))
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
            self._write_failure_status(run_directory, "CONTROL_FILES_MISSING")
            raise SwatProjectInvalidError("SWAT+ project must include time.sim and print.prt", details={"workspace": str(workspace)})
        control_files = {
            "time_sim": _configure_time_sim(time_sim, config),
            "print_prt": _configure_print_prt(print_prt, config),
        }
        stale_outputs = self._clear_recognized_outputs(run_directory)
        try:
            compatibility_log = SwatInputCompatibility.normalize_copy(run_directory)
        except SwatInputCompatibilityError as exc:
            self._write_failure_status(run_directory, "INPUT_COMPATIBILITY_PREPARATION_FAILED", exc.details)
            raise SwatProjectInvalidError(
                "SWAT+ input compatibility preparation failed in isolated workspace",
                details={"workspace": str(workspace), **exc.details},
            ) from exc
        input_checksums_before_mutator = self._input_checksums(run_directory)
        workspace_modifications: dict[str, Any] = {"status": "NOT_APPLIED"}
        if workspace_mutator is not None:
            try:
                workspace_modifications = workspace_mutator(run_directory)
            except Exception as exc:
                self._write_failure_status(run_directory, "COUPLED_INPUT_MUTATOR_FAILED", {"message": str(exc)})
                raise SwatProjectInvalidError("Coupled SWAT+ input preparation failed", details={"workspace": str(workspace), "message": str(exc)}) from exc
        if config.run_type == "SWAT_MULTISCALE_COUPLED":
            # Re-check the effective, isolated inputs after any caller-specific
            # crop setup and immediately before the scientific process starts.
            effective_config = replace(config, project_path=workspace)
            effective_preflight = self.preflight(effective_config, target_crop=target_crop)
            if effective_preflight.get("status") != "READY":
                self._write_failure_status(run_directory, "EFFECTIVE_COPY_PREFLIGHT_BLOCKED", effective_preflight)
                require_coupled_preflight_ready(effective_preflight)
        input_checksums_after_mutator = self._input_checksums(run_directory)
        try:
            remaining_compatibility = SwatInputCompatibility.inspect(run_directory)
        except SwatInputCompatibilityError as exc:
            self._write_failure_status(run_directory, "EFFECTIVE_INPUT_VALIDATION_FAILED", exc.details)
            raise SwatProjectInvalidError(
                "SWAT+ effective workspace failed integer input validation",
                details={"workspace": str(workspace), **exc.details},
            ) from exc
        if remaining_compatibility["correction_count"]:
            self._write_failure_status(run_directory, "EFFECTIVE_INTEGER_INPUTS_NOT_NORMALIZED", {
                "correction_count": remaining_compatibility["correction_count"]
            })
            raise SwatProjectInvalidError(
                "SWAT+ effective workspace contains non-normalized integer fields",
                details={"workspace": str(workspace), "correction_count": remaining_compatibility["correction_count"]},
            )
        changed_input_files = sorted(name for name, before in input_checksums_before_mutator.items()
                                     if input_checksums_after_mutator.get(name) != before)
        created_input_files = sorted(name for name in input_checksums_after_mutator
                                     if name not in input_checksums_before_mutator)
        command = [str(config.executable_path.resolve())]
        execution_started_ns = time.time_ns()
        try:
            completed = subprocess.run(command, cwd=run_directory, capture_output=True, text=True,
                                       timeout=config.timeout_seconds, check=False)
        except subprocess.TimeoutExpired as exc:
            duration = time.monotonic() - started
            self._write_failure_status(run_directory, "TIMEOUT", {
                "timeout_seconds": config.timeout_seconds, "duration_seconds": duration,
                "stdout_tail": (exc.stdout or "")[-4000:], "stderr_tail": (exc.stderr or "")[-4000:],
            })
            raise SwatRunFailedError("SWAT+ process timed out", details={
                "timeout_seconds": config.timeout_seconds, "duration_seconds": duration,
                "stdout": (exc.stdout or "")[-4000:], "stderr": (exc.stderr or "")[-4000:],
                "workspace": str(workspace),
            }) from exc
        except OSError as exc:
            self._write_failure_status(run_directory, "EXECUTABLE_START_FAILED", {"message": str(exc)})
            raise SwatRunFailedError("Unable to start SWAT+ executable", details={"workspace": str(workspace)}) from exc
        duration = time.monotonic() - started
        if completed.returncode != 0:
            failure = {
                "status": "FAILED", "reason": "NON_ZERO_EXIT_CODE", "exit_code": completed.returncode,
                "stdout_tail": completed.stdout[-4000:], "stderr_tail": completed.stderr[-4000:],
                "workspace": str(workspace), "input_compatibility": compatibility_log,
            }
            (run_directory / "swat_run_status.json").write_text(json.dumps(failure, indent=2) + "\n", encoding="utf-8")
            raise SwatRunFailedError("SWAT+ process exited with a non-zero status", details={
                "exit_code": completed.returncode, "stdout": completed.stdout[-4000:], "stderr": completed.stderr[-4000:],
                "duration_seconds": duration, "workspace": str(workspace), "command": command,
            })

        success_marker = run_directory / "success.fin"
        if not success_marker.is_file() or success_marker.stat().st_mtime_ns < execution_started_ns:
            failure = {
                "status": "FAILED", "reason": "SUCCESS_MARKER_MISSING_OR_STALE",
                "exit_code": completed.returncode, "stdout_tail": completed.stdout[-4000:],
                "stderr_tail": completed.stderr[-4000:], "workspace": str(workspace),
                "input_compatibility": compatibility_log,
            }
            (run_directory / "swat_run_status.json").write_text(json.dumps(failure, indent=2) + "\n", encoding="utf-8")
            raise SwatRunFailedError("SWAT+ returned zero but did not create a current success.fin marker", details=failure)

        try:
            parsed: SwatParsedOutput = SwatOutputParser(
                output_frequency=config.output_frequency, outlet_unit=config.outlet_unit,
            ).parse(
                run_directory, start_date=config.simulation_start, end_date=config.simulation_end,
            )
        except FileNotFoundError as exc:
            self._write_failure_status(run_directory, "REQUIRED_OUTPUT_MISSING", {"message": str(exc)})
            raise SwatOutputNotFoundError("SWAT+ completed but did not generate a recognized hydrological output", details={
                "workspace": str(workspace), "expected": "output_wb* and/or output_channel*",
            }) from exc
        except ValueError as exc:
            self._write_failure_status(run_directory, "OUTPUT_PARSE_FAILED", {"message": str(exc)})
            raise SwatOutputParseError("SWAT+ output could not be parsed", details={"workspace": str(workspace)}) from exc
        output_generation = {
            str(path.relative_to(workspace)): {"sha256": _sha256(path), "mtime_ns": path.stat().st_mtime_ns,
                                                "generated_after_start": path.stat().st_mtime_ns >= execution_started_ns}
            for path in parsed.source_files
        }
        if not all(item["generated_after_start"] for item in output_generation.values()):
            self._write_failure_status(run_directory, "OUTPUT_PREDATES_EXECUTION", output_generation)
            raise SwatOutputParseError("Parsed SWAT+ output predates this execution", details={"workspace": str(workspace)})

        run_status = {
            "status": "COMPLETED", "exit_code": completed.returncode,
            "start_date": config.simulation_start.isoformat(), "end_date": config.simulation_end.isoformat(),
            "warmup_years": config.warmup_period, "workspace": str(workspace),
            "success_marker": str(success_marker), "input_compatibility": compatibility_log,
            "output_checksums": {name: item["sha256"] for name, item in output_generation.items()},
        }
        (run_directory / "swat_run_status.json").write_text(json.dumps(run_status, indent=2, sort_keys=True) + "\n", encoding="utf-8")

        return SwatRunResult(
            status="COMPLETED", run_id=config.run_id, watershed_id=config.watershed_id,
            start_date=config.simulation_start.isoformat(), end_date=config.simulation_end.isoformat(),
            workspace=str(workspace), exit_code=completed.returncode, duration_seconds=duration,
            stdout=completed.stdout, stderr=completed.stderr, records=parsed.records, hru_results=parsed.hru_results,
            plant_results=parsed.plant_results, channel_results=parsed.channel_results,
            management_events=parsed.management_events,
            water_balance=parsed.water_balance, output_files=parsed.output_files,
            provenance={
                "evidence_type": "REAL_SWAT_PLUS", "engine": "SWAT+", "command": command,
                "executable_path": str(config.executable_path.resolve()), "executable_sha256": _sha256(config.executable_path),
                "executable_version": self._version_from_run(completed.stdout, run_directory), "source_project": str(source_root),
                "source_file_cio_sha256": _sha256(input_directory / "file.cio"), "workspace": str(workspace),
                "output_checksums": {str(path.relative_to(workspace)): _sha256(path) for path in parsed.source_files},
                "stale_workspace_outputs_removed": stale_outputs, "configured_control_files": control_files,
                "input_compatibility": compatibility_log,
                "workspace_modifications": workspace_modifications,
                "input_checksums_before_mutator": input_checksums_before_mutator,
                "input_checksums_after_mutator": input_checksums_after_mutator,
                "input_checksum_diff": {"changed": changed_input_files, "created": created_input_files,
                                        "unchanged": sorted((set(input_checksums_before_mutator) & set(input_checksums_after_mutator)) - set(changed_input_files))},
                "output_generation": output_generation,
                "output_frequency": config.output_frequency, "warmup_period": config.warmup_period,
            },
        )
