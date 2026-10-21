"""Scientific exports preserve frozen data, alignment, uncertainty and auth."""
import csv
import hashlib
import io
import json
import shutil

import pytest
from httpx import ASGITransport, AsyncClient
from matplotlib.figure import Figure

from app.main import app
from app.services.scientific_exports import DOMAIN, ScientificExport


@pytest.mark.parametrize("variant", ["PRIMARY", "EXCLUDE_ESTIMATED"])
def test_metrics_and_contrasts_keep_frozen_values_and_reference_orientation(variant):
    export = ScientificExport(variant=variant)
    headers, rows, _ = export.table("performance")
    assert headers == ["Métrica", "A", "B", "C", "D"]
    for index, metric in enumerate(("rmse", "mae", "nse", "kge", "pbias")):
        for col, arm in enumerate("ABCD", 1):
            assert rows[index][col] == f"{export.evaluation['metrics'][arm][metric]['value']:.2f}"
    _, rows, _ = export.table("contrasts")
    assert [row[0] for row in rows] == ["B−A", "C−A", "D−B", "D−C", "D−A"]
    main = export.evaluation["contrasts"]["D_vs_A"]
    assert float(rows[-1][2]) == round(main["rmse_reduction_m3s"], 2) < 0
    assert rows[-1][-1] == "Incluye 0"
    assert rows[0][-1] == "Excluye 0"


def test_temporal_export_uses_actual_protocol_and_frozen_plant_contract():
    export = ScientificExport()
    assert [row[:2] for row in export.partition_rows()] == [
        ["Warm-up", "2000–2004 / 60"], ["CALIBRATION", "2005–2012 / 96"],
        ["TRAIN", "2013–2017 / 60"], ["VALIDATION", "2018–2020 / 36"],
        ["TEST", "2021–2025 / 60"],
    ]
    _, rows, _ = export.table("plant-mapping")
    contract = export._plant_contract()
    assert contract["derivation_year"] == 2010
    assert len(rows) == 10
    assert rows[0][3].startswith(f"{contract['summary']['swat_lai_contract']['lai_pot']:.4f}")
    assert "sin calibrar" in rows[-1][-1]
    assert "sin calibrar" in rows[-2][-1]


def test_hydrograph_preserves_calendar_gaps_and_sensitivity_support():
    import numpy as np

    for variant, eligible in (("PRIMARY", 60), ("EXCLUDE_ESTIMATED", 36)):
        export = ScientificExport(variant=variant)
        figure = Figure()
        export._hydrograph(figure)
        lines = figure.axes[0].lines
        assert [line.get_label() for line in lines] == ["USGS", "A", "B", "C", "D"]
        assert all(len(line.get_xdata()) == 60 for line in lines)
        assert all(np.isfinite(line.get_ydata()).sum() == eligible for line in lines)
        assert lines[0].get_xdata()[0].isoformat() == "2021-01-01"
        assert lines[0].get_xdata()[-1].isoformat() == "2025-12-01"


@pytest.mark.parametrize("key", [item["id"] for item in ScientificExport().catalog()["entries"]])
def test_all_exports_render_with_correct_formats_without_changing_sources(key):
    export = ScientificExport()
    paths = [DOMAIN / "south_fork_test_delivery_4_v1.json", DOMAIN / "test_v1/monthly-predictions.csv",
             DOMAIN / "paper_v1/artifact-manifest.json"]
    before = {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
    assert export.render(key, "png").startswith(b"\x89PNG\r\n\x1a\n")
    assert b"<svg" in export.render(key, "svg")
    assert export.render(key, "pdf").startswith(b"%PDF-")
    entry = next(item for item in export.catalog()["entries"] if item["id"] == key)
    if "csv" in entry["formats"]:
        rows = list(csv.reader(io.StringIO(export.render(key, "csv").decode("utf-8-sig"))))
        assert len(rows) == len(export.table(key)[1]) + 1
    else:
        with pytest.raises(ValueError):
            export.render(key, "csv")
    assert before == {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}


def test_tampered_sources_fail_closed(tmp_path):
    shutil.copytree(DOMAIN / "test_v1", tmp_path / "test_v1")
    for name in ("south_fork_test_delivery_4_v1.json", "south_fork_multiyear_protocol_v1.json",
                 "south_fork_multiyear_delivery_2_v1.json"):
        shutil.copyfile(DOMAIN / name, tmp_path / name)
    export = ScientificExport(tmp_path)
    (tmp_path / "test_v1/monthly-predictions.csv").write_text("altered")
    with pytest.raises(ValueError, match="integridad"):
        export._predictions()
    path = tmp_path / "south_fork_multiyear_delivery_2_v1.json"
    data = json.loads(path.read_bytes())
    data["frozen_plant_contract"]["derivation_year"] = 2019
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="contrato vegetal"):
        export.table("plant-mapping")
    path = tmp_path / "south_fork_multiyear_protocol_v1.json"
    path.write_text("{}")
    with pytest.raises(ValueError, match="integridad"):
        ScientificExport(tmp_path)


@pytest.mark.asyncio
async def test_export_endpoints_require_auth_validate_inputs_and_preserve_existing_downloads():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        prefix = "/api/v1/research/south-fork"
        for path in ("/exports", "/exports/performance/png"):
            assert (await client.get(prefix + path)).status_code == 401
        login = await client.post("/api/v1/auth/login", json={
            "email": "investigador@digitaltwin.org", "password": "Investiga123!"})
        headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
        catalog = await client.get(prefix + "/exports", headers=headers)
        assert catalog.status_code == 200
        assert len(catalog.json()["entries"]) == 8
        response = await client.get(prefix + "/exports/performance/csv?variant=EXCLUDE_ESTIMATED", headers=headers)
        assert response.status_code == 200
        assert "sf-test-v1_performance_exclude_estimated.csv" in response.headers["content-disposition"]
        assert response.headers["cache-control"] == "private, no-store"
        assert "Métrica,A,B,C,D" in response.content.decode("utf-8-sig")
        for path, status in (("/exports/missing/png", 404), ("/exports/performance/exe", 422),
                             ("/exports/monthly-hydrograph/csv", 422),
                             ("/exports/performance/png?variant=INVALID", 422)):
            assert (await client.get(prefix + path, headers=headers)).status_code == status
        # Existing research download remains reachable and returns its original bytes.
        report = await client.get(prefix + "/artifacts/report", headers=headers)
        assert report.status_code == 200
        assert report.content == (DOMAIN / "south_fork_test_delivery_4_v1.json").read_bytes()
