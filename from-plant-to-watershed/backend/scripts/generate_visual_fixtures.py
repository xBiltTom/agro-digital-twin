"""Deterministic contract fixtures. Synthetic tests, never South Fork results."""
from __future__ import annotations

from datetime import date
import json
from pathlib import Path
import sys

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))
from app.schemas.playback import CropState, Evidence, PlaybackPage, PlaybackRecord, PlantSample, VariableState

OUT = BACKEND.parent / "frontend/tests/fixtures/twin-visual-fixtures.json"


def variable(value, unit, evidence=Evidence.SIMPLIFIED_FSPM):
    return VariableState(value=value, unit=unit,
        evidence=evidence if value is not None else Evidence.NOT_AVAILABLE,
        source="DETERMINISTIC_TEST_FIXTURE", availability="AVAILABLE" if value is not None else "NOT_AVAILABLE",
        limitation="Synthetic contract input, not a South Fork result" if value is not None else "No test value")


def frame(run, day, *, crop=True, height=0.2, lai=0.4, rain=0.0, samples=True,
          baseline=False, resolution="DAILY", hydro=True):
    active = crop and not baseline
    field = ({"height_m": variable(height, "m"), "lai": variable(lai, "m2_leaf/m2_ground"),
        "root_depth_m": variable(0.1 if height == 0.2 else 0.9, "m"),
        "biomass_g_plant": variable(12.0 if height == 0.2 else 650.0, "g/plant"),
        "canopy_cover_fraction": variable(0.1 if height == 0.2 else 0.8, "fraction"),
        "water_stress": variable(0.2, "fraction [0, 1]"),
        "actual_transpiration_mm_day": variable(1.0, "mm/day"),
        "soil_moisture_vol_percent": variable(24.0, "volumetric percent", Evidence.ASSUMED)} if active else {})
    plants = ([PlantSample(plant_id="test-plant-1", x_m=0.5, y_m=1.0,
        variables={"height_m": variable(height, "m"), "lai": variable(lai, "m2_leaf/m2_ground"),
                   "phenological_stage": variable("V2" if height == 0.2 else "REPRODUCTIVE", "category")})]
        if active and samples else [])
    return PlaybackRecord(simulation_id=run, date=date.fromisoformat(day), resolution=resolution,
        run_type="SWAT_STANDARD_BASELINE" if baseline else "SWAT_MULTISCALE_COUPLED",
        watershed_id="TEST_BASIN_ONLY", watershed_code="TEST_NOT_SOUTH_FORK",
        spatial_support="TEST_FIXTURE", crop=None if baseline else CropState(
            active=active, crop="maize" if active else None, season_id="TEST_SEASON" if active else None,
            phenological_stage="V2" if height == 0.2 and active else "REPRODUCTIVE" if active else None,
            window_status="APPROXIMATE_PLANTING_WINDOW", source="DETERMINISTIC_TEST_FIXTURE"),
        weather={"precipitation_mm": variable(rain, "mm/day" if resolution == "DAILY" else "mm/period", Evidence.SYNTHETIC)},
        field=field, plant_samples=plants,
        hydrology={"streamflow_m3s": variable(2.0 if hydro else None, "m3/s", Evidence.MODELLED_SWAT_PLUS),
                   "soil_water_mm": variable(140.0 if hydro else None, "mm", Evidence.MODELLED_SWAT_PLUS)},
        availability={"weather": "AVAILABLE" if rain is not None else "NOT_AVAILABLE",
                      "field": "AVAILABLE" if field else "NOT_AVAILABLE",
                      "plant_samples": "AVAILABLE" if plants else "NOT_AVAILABLE",
                      "hydrology": "AVAILABLE" if hydro else "NOT_AVAILABLE", "hru_results": "NOT_AVAILABLE"},
        limitations=["DETERMINISTIC TEST FIXTURE; not a scientific South Fork result"])


def page(run, rows, *, resolutions=None):
    return PlaybackPage(simulation_id=run, simulation_status="COMPLETED",
        artifact_status="AVAILABLE" if rows else "NOT_AVAILABLE",
        resolution=rows[0].resolution if rows else None,
        available_resolutions=resolutions or ([rows[0].resolution] if rows else []),
        total=len(rows), offset=0, limit=100, records=rows,
        provenance={"fixture": True, "scientific_result": False},
        limitations=["Synthetic deterministic contract fixture; not South Fork data"])


def generate():
    coupled = "fixture-coupled"
    pages = {
        "coupled_daily": page(coupled, [frame(coupled, "2020-05-10", height=0.2, lai=0.4, rain=0),
            frame(coupled, "2020-08-10", height=2.1, lai=4.2, rain=None),
            frame(coupled, "2020-11-10", crop=False, rain=0)], resolutions=["MONTHLY", "DAILY"]),
        "baseline": page("fixture-baseline", [frame("fixture-baseline", "2020-05-10", baseline=True, rain=3)]),
        "historical": page("fixture-historical", []),
        "incomplete": page("fixture-incomplete", [frame("fixture-incomplete", "2020-06-10", height=None, lai=1.2, samples=False)]),
        "coupled_monthly": page(coupled, [frame(coupled, "2020-05-01", resolution="MONTHLY", baseline=True,
            rain=54, hydro=True)], resolutions=["MONTHLY", "DAILY"]),
    }
    # Monthly SWAT+ frame has no FSPM; its run type remains coupled.
    pages["coupled_monthly"].records[0].run_type = "SWAT_MULTISCALE_COUPLED"
    return {"fixture_version": 1, "test_only": True,
            "disclaimer": "Synthetic deterministic contract inputs; no validated South Fork result",
            "pages": {key: value.model_dump(mode="json") for key, value in pages.items()}}


if __name__ == "__main__":
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(generate(), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(OUT)
