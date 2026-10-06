"""Validate the local source build's explicit instrumentation contract."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

SOURCE_COMMIT = "77b722bac716c32f2fba6b4e3f9dd6ea4b008e3d"
STORAGE_FILE = "channel_storage_day.txt"


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
    for name, checksum in manifest["dynamic_libraries_sha256"].items():
        library = Path(name)
        if not library.is_file() or hashlib.sha256(library.read_bytes()).hexdigest() != checksum:
            raise ValueError(f"Research engine runtime library changed: {name}")
    return {**manifest, "manifest_sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
