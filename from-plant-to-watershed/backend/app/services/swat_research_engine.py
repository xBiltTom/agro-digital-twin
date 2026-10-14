"""Validate the local source build's explicit instrumentation contract."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

SOURCE_COMMIT = "77b722bac716c32f2fba6b4e3f9dd6ea4b008e3d"
STORAGE_FILE = "channel_storage_day.txt"


def runtime_command(executable: Path) -> list[str]:
    """Launch the identical ELF binary with its hash-verified original runtime."""
    marker = executable.parent / "runtime-manifest.json"
    if not marker.is_file():
        return [str(executable.resolve())]
    runtime = json.loads(marker.read_text())
    if hashlib.sha256(executable.read_bytes()).hexdigest() != runtime["executable_sha256"]:
        raise ValueError("Bundled executable checksum mismatch")
    root = executable.parent / "runtime"
    for name, checksum in runtime["libraries"].items():
        if Path(name).name != name or hashlib.sha256((root / name).read_bytes()).hexdigest() != checksum:
            raise ValueError("Bundled runtime library checksum mismatch")
    loader_name = runtime["loader"]
    if Path(loader_name).name != loader_name or loader_name not in runtime["libraries"]:
        raise ValueError("Invalid bundled ELF loader")
    return [str((root / loader_name).resolve()), "--library-path", str(root.resolve()), str(executable.resolve())]


def engine_manifest(executable: Path) -> dict | None:
    path = executable.parent / "engine-manifest.json"
    if not path.is_file():
        return None
    manifest = json.loads(path.read_text())
    if (manifest.get("schema_version") != "swat-research-build/v1" or
            manifest.get("source", {}).get("commit") != SOURCE_COMMIT or
            manifest.get("storage_output", {}).get("filename") != STORAGE_FILE or
            manifest.get("storage_output", {}).get("marker") != "channel-storage/v1" or
            manifest.get("numerical_policy") != {"trap": ["invalid", "zero", "overflow"], "allow": ["underflow"]}):
        raise ValueError("Unsupported research engine manifest")
    if hashlib.sha256(executable.read_bytes()).hexdigest() != manifest["executable_sha256"]:
        raise ValueError("Research engine executable differs from its manifest")
    bundled_runtime = executable.parent / "runtime-manifest.json"
    if bundled_runtime.is_file():
        runtime_command(executable)
    resolved_libraries = {}
    for name, checksum in manifest["dynamic_libraries_sha256"].items():
        library = executable.parent / "runtime" / Path(name).name if bundled_runtime.is_file() else Path(name)
        resolved_libraries[name] = str(library)
        if not library.is_file() or hashlib.sha256(library.read_bytes()).hexdigest() != checksum:
            raise ValueError(f"Research engine runtime library changed: {name}")
    return {**manifest, "resolved_runtime_libraries": resolved_libraries, "manifest_sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
