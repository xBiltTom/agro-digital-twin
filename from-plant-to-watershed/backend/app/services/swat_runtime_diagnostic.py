"""Audited runtime-only diagnostic for the exact GNU SWAT+ 61.0.2.61 binary.

No model routine is changed. A fresh binary copy changes one byte of main's
_gfortran_set_fpe argument, from 29 to 13, removing only the underflow trap.
This is an explicit development intervention, not an official engine release.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

SOURCE_SHA256 = "5f0e6b43833bce1dbd6d416813bffc7b742dcff79ae1e7008d8f65bacd9b314e"
STARTUP_SEQUENCE = bytes.fromhex("bf1d000000e86cb13200e855f4ffff")


def prepare_underflow_diagnostic(source: Path, destination: Path) -> dict:
    source, destination = source.resolve(), destination.resolve()
    manifest = destination.with_suffix(".json")
    if source == destination or destination.exists() or manifest.exists():
        raise ValueError("Use a fresh destination; preserve the official binary and prior diagnostics")
    data = source.read_bytes()
    if hashlib.sha256(data).hexdigest() != SOURCE_SHA256:
        raise ValueError("Runtime diagnostic is restricted to the exact audited Linux GNU binary")
    offset = data.find(STARTUP_SEQUENCE)
    if offset < 0 or data.find(STARTUP_SEQUENCE, offset + 1) >= 0:
        raise ValueError("Expected unique audited main/_gfortran_set_fpe startup instruction")
    corrected = bytearray(data)
    corrected[offset + 1] = 13
    if [i for i, (a, b) in enumerate(zip(data, corrected, strict=True)) if a != b] != [offset + 1]:
        raise ValueError("Runtime diagnostic must change exactly one startup flag byte")
    report = {"classification": "UNDERFLOW_RUNTIME_DIAGNOSTIC", "official_release": False,
        "source_executable": str(source), "source_sha256": SOURCE_SHA256,
        "executable": str(destination), "executable_sha256": hashlib.sha256(corrected).hexdigest(),
        "changed_byte_offset": offset + 1, "before_byte": 29, "after_byte": 13,
        "runtime_call": "main -> _gfortran_set_fpe",
        "traps_before": ["invalid", "zero", "overflow", "underflow"],
        "traps_after": ["invalid", "zero", "overflow"],
        "model_routines_changed": False,
        "limitation": "Derived diagnostic executable; production/research engine selection requires a reproducible source build or an official release with this runtime policy.",
        "reference": "https://gcc.gnu.org/onlinedocs/gfortran/_005fgfortran_005fset_005ffpe.html"}
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("xb") as handle:
        handle.write(corrected)
    destination.chmod(source.stat().st_mode & 0o777)
    with manifest.open("x") as handle:
        json.dump(report, handle, indent=2, allow_nan=False)
        handle.write("\n")
    if hashlib.sha256(source.read_bytes()).hexdigest() != SOURCE_SHA256:
        raise ValueError("Official binary changed during preparation")
    return report
