"""Reproducible USDA NASS CDL-to-HRU overlay.

The overlay is deliberately a small, read-only classification step.  It does
not alter SWAT+ outputs or infer a crop from the existing generic ``AGRL``
land-use label.  HRU crop fractions are calculated from the official CDL
pixels in the HRU geometry and are then consumed by the explicit SWAT+
land-use mapper.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any


# USDA/NASS CDL classes that contain maize in the Iowa 2019 legend.  The
# double-crop classes are retained because they explicitly contain corn;
# sweet and popcorn are also maize.  82/83 are *developed/water* in Iowa 2019
# and must not be treated as crop classes.
CORN_CODES = frozenset({1, 12, 13, 225, 226, 228, 237, 241})

# Iowa 2019 CDL classes that contain soybeans.  A double-crop pixel can be in
# both this set and CORN_CODES (code 241); the provenance records this overlap
# explicitly, while ``other_crop_fraction`` uses the union so fractions remain
# interpretable as a crop/non-crop partition.
SOYBEAN_CODES = frozenset({5, 26, 239, 240, 241, 254})

# Cultivated-crop classes in the CDL legend.  61 (fallow/idle cropland) is
# retained for the watershed agricultural-fraction diagnostic, but it can
# never make an HRU a corn HRU by itself.
# The Iowa metadata groups crop classes as 1--60, 66--80 and 204--255.
# Using explicit ranges preserves the official category definition while
# allowing state-specific classes that do not appear in this clipped raster.
AGRICULTURAL_CODES = frozenset(range(1, 61)) | frozenset(range(66, 81)) | frozenset(range(204, 256))

# 0 is the clip/background value and 81 is the CDL clouds/no-data class.
NO_DATA_CODES = frozenset({0, 81})

_KNOWN_CLASS_NAMES = {
    1: "Corn", 5: "Soybeans", 12: "Sweet Corn", 13: "Pop or Orn Corn",
    26: "Dbl Crop WinWht/Soybeans", 225: "Dbl Crop WinWht/Corn",
    226: "Dbl Crop Oats/Corn", 228: "Dbl Crop Triticale/Corn",
    237: "Dbl Crop Barley/Corn", 239: "Dbl Crop Soybeans/Cotton",
    240: "Dbl Crop Soybeans/Oats", 241: "Dbl Crop Corn/Soybeans",
    254: "Dbl Crop Barley/Soybeans", 82: "Developed", 83: "Water",
}


@dataclass(frozen=True)
class CDLOverlayConfig:
    year: int
    corn_majority_threshold: float = 0.50
    source_url: str = "https://www.nass.usda.gov/Research_and_Science/Cropland/metadata/metadata_ia19.htm"
    query_url: str | None = None


class CDLHRUOverlay:
    """Calculate and persist a static CDL snapshot for a SWAT+ HRU layer."""

    @staticmethod
    def _sha256(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    @staticmethod
    def compute(
        hru_path: str | Path,
        cdl_path: str | Path,
        output_parquet: str | Path,
        provenance_path: str | Path,
        *,
        config: CDLOverlayConfig,
    ) -> dict[str, Any]:
        """Return summary and write one row per HRU to Parquet.

        Pixel fractions are calculated only from valid pixels intersecting the
        HRU polygon.  The area-weighted watershed fractions therefore cannot be
        inflated by the rectangular crop/background around the basin.
        """
        try:
            import geopandas as gpd
            import numpy as np
            import pandas as pd
            import rasterio
            from rasterio.mask import mask
        except ImportError as exc:  # pragma: no cover - environment contract
            raise RuntimeError("CDL overlay requires geopandas, pandas, numpy and rasterio") from exc

        hru_path, cdl_path = Path(hru_path), Path(cdl_path)
        output_parquet, provenance_path = Path(output_parquet), Path(provenance_path)
        if not hru_path.is_file() or not cdl_path.is_file():
            raise FileNotFoundError("HRU layer and official CDL raster are required")
        if not 0.0 < config.corn_majority_threshold <= 1.0:
            raise ValueError("corn_majority_threshold must be in (0, 1]")

        hrus = gpd.read_file(hru_path)
        with rasterio.open(cdl_path) as raster:
            if hrus.crs is None:
                raise ValueError("HRU layer must have a CRS")
            if raster.crs is None:
                raise ValueError("CDL raster must have a CRS")
            if hrus.crs != raster.crs:
                hrus = hrus.to_crs(raster.crs)
            pixel_area_m2 = abs(float(raster.transform.a * raster.transform.e))
            rows: list[dict[str, Any]] = []
            totals: dict[int, int] = {}
            for _, hru in hrus.iterrows():
                values, _ = mask(raster, [hru.geometry.__geo_interface__], crop=True, filled=True, nodata=0)
                flat = values[0].astype("int64", copy=False).ravel()
                valid = flat[~np.isin(flat, list(NO_DATA_CODES))]
                counts = {int(code): int(count) for code, count in zip(*np.unique(valid, return_counts=True))}
                valid_pixels = int(valid.size)
                if valid_pixels == 0:
                    raise ValueError(f"HRU {hru['hru_id']} has no valid CDL pixels")
                for code, count in counts.items():
                    totals[code] = totals.get(code, 0) + count
                corn_pixels = sum(count for code, count in counts.items() if code in CORN_CODES)
                soybean_pixels = sum(count for code, count in counts.items() if code in SOYBEAN_CODES)
                agricultural_pixels = sum(count for code, count in counts.items() if code in AGRICULTURAL_CODES)
                other_crop_pixels = sum(
                    count for code, count in counts.items()
                    if code in AGRICULTURAL_CODES and code not in CORN_CODES and code not in SOYBEAN_CODES
                )
                non_crop_pixels = valid_pixels - agricultural_pixels
                dominant_code = max(counts, key=counts.get)
                rows.append({
                    "hru_id": int(hru["hru_id"]),
                    "cdl_year": config.year,
                    "hru_area_ha": float(hru.geometry.area / 10000.0),
                    "valid_pixel_count": valid_pixels,
                    "valid_area_ha": valid_pixels * pixel_area_m2 / 10000.0,
                    "valid_pixel_fraction_of_crop_window": valid_pixels / float(flat.size),
                    "corn_pixel_count": corn_pixels,
                    "corn_fraction": corn_pixels / valid_pixels,
                    "soybean_pixel_count": soybean_pixels,
                    "soybean_fraction": soybean_pixels / valid_pixels,
                    "other_crop_pixel_count": other_crop_pixels,
                    "other_crop_fraction": other_crop_pixels / valid_pixels,
                    "non_crop_pixel_count": non_crop_pixels,
                    "non_crop_fraction": non_crop_pixels / valid_pixels,
                    "agricultural_pixel_count": agricultural_pixels,
                    "agricultural_fraction": agricultural_pixels / valid_pixels,
                    "corn_majority": bool(corn_pixels / valid_pixels >= config.corn_majority_threshold),
                    "dominant_class": int(dominant_code),
                    "dominant_class_name": _KNOWN_CLASS_NAMES.get(int(dominant_code), f"CDL_{int(dominant_code)}"),
                    "coverage_quality": "VALID" if valid_pixels else "NO_VALID_PIXELS",
                    "class_counts": json.dumps(counts, sort_keys=True),
                })

        frame = pd.DataFrame(rows).sort_values("hru_id")
        output_parquet.parent.mkdir(parents=True, exist_ok=True)
        provenance_path.parent.mkdir(parents=True, exist_ok=True)
        frame.to_parquet(output_parquet, index=False)
        total_valid = sum(totals.values())
        area_weight = frame["valid_area_ha"].to_numpy(dtype=float)
        total_area = float(area_weight.sum())
        corn_fraction = sum(count for code, count in totals.items() if code in CORN_CODES) / total_valid
        soybean_fraction = sum(count for code, count in totals.items() if code in SOYBEAN_CODES) / total_valid
        agricultural_fraction = sum(count for code, count in totals.items() if code in AGRICULTURAL_CODES) / total_valid
        other_crop_fraction = sum(
            count for code, count in totals.items()
            if code in AGRICULTURAL_CODES and code not in CORN_CODES and code not in SOYBEAN_CODES
        ) / total_valid
        summary = {
            "status": "COMPLETED",
            "classification": "STATIC_CDL_SNAPSHOT",
            "cdl_year": config.year,
            "hru_count": len(rows),
            "corn_hru_count": int(frame["corn_majority"].sum()),
            "corn_hru_ids": [int(value) for value in frame.loc[frame["corn_majority"], "hru_id"]],
            "corn_majority_threshold": config.corn_majority_threshold,
            "corn_fraction_valid_pixels": corn_fraction,
            "soybean_fraction_valid_pixels": soybean_fraction,
            "other_crop_fraction_valid_pixels": other_crop_fraction,
            "non_crop_fraction_valid_pixels": 1.0 - agricultural_fraction,
            "agricultural_fraction_valid_pixels": agricultural_fraction,
            "valid_pixel_count": total_valid,
            "valid_area_ha": total_area,
            "pixel_area_m2": pixel_area_m2,
            "crs": str(raster.crs),
            "raster_resolution_m": [float(raster.res[0]), float(raster.res[1])],
            "source": {
                "metadata_url": config.source_url,
                "query_url": config.query_url,
                "raster_path": str(cdl_path),
                "raster_sha256": CDLHRUOverlay._sha256(cdl_path),
                "hru_path": str(hru_path),
                "hru_sha256": CDLHRUOverlay._sha256(hru_path),
            },
            "class_sets": {
                "corn_codes": sorted(CORN_CODES),
                "soybean_codes": sorted(SOYBEAN_CODES),
                "agricultural_codes": sorted(AGRICULTURAL_CODES),
                "excluded_no_data_codes": sorted(NO_DATA_CODES),
                "fraction_definition": "corn/soybean fractions may overlap for explicit double-crop classes; other_crop_fraction is the agricultural union excluding both sets; non_crop_fraction is the complement of agricultural_fraction",
            },
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "output_parquet": str(output_parquet),
        }
        provenance_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return summary
