"""Local normalized CSV climate provider; NetCDF is intentionally not required for MVP."""

import csv
import json
from pathlib import Path
from typing import Any


class Cmip6FileProvider:
    REQUIRED_METADATA = {"scenario", "gcm", "member", "period", "variables", "units", "calendar", "source"}

    def __init__(self, csv_path: str | Path, metadata_path: str | Path):
        self.csv_path, self.metadata_path = Path(csv_path), Path(metadata_path)

    def load(self) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        metadata = json.loads(self.metadata_path.read_text())
        missing = self.REQUIRED_METADATA - metadata.keys()
        if missing:
            raise ValueError(f"CMIP6 metadata missing: {', '.join(sorted(missing))}")
        with self.csv_path.open(newline="") as handle:
            rows = list(csv.DictReader(handle))
        required_columns = {"date", "precip_mm", "temp_c"}
        if not rows or not required_columns <= rows[0].keys():
            raise ValueError("normalized CMIP6 CSV requires date, precip_mm, temp_c")
        return [{**row, "precip_mm": float(row["precip_mm"]), "temp_c": float(row["temp_c"])} for row in rows], metadata
