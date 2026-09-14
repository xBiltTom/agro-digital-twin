from pathlib import Path

import pytest

from app.services.cdl_hru_overlay import (
    AGRICULTURAL_CODES,
    CORN_CODES,
    NO_DATA_CODES,
    SOYBEAN_CODES,
    CDLHRUOverlay,
    CDLOverlayConfig,
)


def test_iowa_cdl_classes_do_not_treat_developed_or_water_as_corn():
    assert {1, 12, 13}.issubset(CORN_CODES)
    assert {5, 26}.issubset(SOYBEAN_CODES)
    assert not ({82, 83} & CORN_CODES)
    assert {0, 81}.issubset(NO_DATA_CODES)
    assert not ({82, 83} & AGRICULTURAL_CODES)


def test_overlay_persists_required_crop_fractions(tmp_path: Path):
    geopandas = pytest.importorskip("geopandas")
    numpy = pytest.importorskip("numpy")
    rasterio = pytest.importorskip("rasterio")
    from shapely.geometry import box
    from rasterio.transform import from_origin

    hru_path = tmp_path / "hrus.gpkg"
    raster_path = tmp_path / "cdl.tif"
    output_path = tmp_path / "hru_crop_composition.parquet"
    provenance_path = tmp_path / "hru_crop_provenance.json"
    geopandas.GeoDataFrame(
        {"hru_id": [1, 2], "geometry": [box(0, 0, 60, 60), box(60, 0, 120, 60)]},
        crs="EPSG:5070",
    ).to_file(hru_path, driver="GPKG")
    # 30 m pixels: first HRU has corn/soybean/forest; second has a
    # corn-soybean double-crop code and developed pixels.
    values = numpy.array([[1, 5, 63, 241], [1, 5, 63, 82]], dtype="uint8")
    with rasterio.open(
        raster_path,
        "w",
        driver="GTiff",
        height=2,
        width=4,
        count=1,
        dtype="uint8",
        crs="EPSG:5070",
        transform=from_origin(0, 60, 30, 30),
    ) as dst:
        dst.write(values, 1)

    summary = CDLHRUOverlay.compute(
        hru_path,
        raster_path,
        output_path,
        provenance_path,
        config=CDLOverlayConfig(year=2019, corn_majority_threshold=0.5),
    )
    frame = __import__("pandas").read_parquet(output_path)
    required = {
        "hru_id", "hru_area_ha", "corn_fraction", "soybean_fraction",
        "other_crop_fraction", "non_crop_fraction", "dominant_class",
        "cdl_year", "coverage_quality",
    }
    assert required.issubset(frame.columns)
    assert summary["hru_count"] == 2
    assert frame["coverage_quality"].eq("VALID").all()
    assert (frame["corn_fraction"] >= 0).all()
    assert (frame["soybean_fraction"] >= 0).all()
    # The partition is mutually exclusive except for documented double-crop
    # overlap in the corn/soybean diagnostics; this fixture has one such pixel.
    assert frame.loc[frame.hru_id == 2, "non_crop_fraction"].iloc[0] > 0
    assert frame.loc[frame.hru_id == 2, "corn_fraction"].iloc[0] > 0
    assert provenance_path.is_file()
