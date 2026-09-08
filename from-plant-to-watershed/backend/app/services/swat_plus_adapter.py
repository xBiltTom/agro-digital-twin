from __future__ import annotations

import os
from pathlib import Path
import subprocess
import hashlib
from typing import Any


class SwatPlusAdapter:
    def __init__(self, executable: str | None = None, project_dir: str | None = None):
        self.executable = Path(executable or os.getenv("SWAT_PLUS_EXECUTABLE", ""))
        self.project_dir = Path(project_dir or os.getenv("SWAT_PLUS_PROJECT_DIR", ""))

    def capability(self) -> dict[str, Any]:
        active = self.executable.is_file() and self.project_dir.is_dir()
        return {"status": "ACTIVE" if active else "NOT_AVAILABLE", "executable": str(self.executable),
                "project_dir": str(self.project_dir), "reason": None if active else "executable/project not configured",
                "project_manifest": str(self.project_dir / "project_manifest.json") if active else None}

    def run(self, timeout_seconds: int = 120) -> dict[str, Any]:
        if self.capability()["status"] != "ACTIVE":
            raise RuntimeError("SWAT_PLUS is NOT_AVAILABLE")
        command = [str(self.executable)]
        completed = subprocess.run(command, cwd=self.project_dir, capture_output=True, text=True,
                                   timeout=timeout_seconds, check=False)
        result = {"exit_code": completed.returncode, "stdout": completed.stdout, "stderr": completed.stderr,
                  "command": command, "project_dir": str(self.project_dir),
                  "executable_sha256": hashlib.sha256(self.executable.read_bytes()).hexdigest(),
                  "status": "COMPLETED" if completed.returncode == 0 else "FAILED", "evidence_type": "REAL"}
        if completed.returncode != 0:
            raise RuntimeError(f"SWAT+ failed with exit code {completed.returncode}: {completed.stderr[-500:]}")
        return result
