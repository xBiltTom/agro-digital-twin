import json
from types import SimpleNamespace

import pytest

from app.services.swat_crop_chain_diagnostic import SwatCropChainDiagnostic
from app.services.swat_plant_parameter_mapper import SwatPlantParameterMapper
import scripts.run_final_south_fork as runner


def _field(*, fspm_crop="sorghum_proxy", target_plant_name="grsg"):
    return {
        "fspm_crop": fspm_crop,
        "target_plant_name": target_plant_name,
        "swat_lai_contract": {
            "lai_pot": 4.0, "frac_hu1": 0.18, "lai_max1": 0.16,
            "frac_hu2": 0.50, "lai_max2": 0.86, "hu_lai_decl": 0.76,
        },
        "plant_height_mean_m": 1.4,
        "root_depth_mean_m": 0.8,
        "canopy_extinction_coefficient": 0.50,
        "biomass_energy_ratio_kg_ha_per_mj_m2": 42.0,
    }


def _sorghum_workspace(path):
    (path / "hru-data.hru").write_text(
        "hru-data.hru\nid name topo hydro soil lu_mgt init surf snow field\n"
        "1 hru01 x x soil corn_lum init null null null\n", encoding="utf-8"
    )
    (path / "landuse.lum").write_text(
        "landuse.lum\nname cal_group plnt_com mgt\n"
        "corn_lum null corn_comm corn_rot\n", encoding="utf-8"
    )
    (path / "plant.ini").write_text(
        "plant.ini\nheader\ncorn_comm 1 1\ncorn n 0\n", encoding="utf-8"
    )
    (path / "management.sch").write_text(
        "management.sch\nheader\ncorn_rot 0 1\npl_hv_summer1 corn\n", encoding="utf-8"
    )
    (path / "lum.dtl").write_text(
        "lum.dtl\nheader\nplant crop\nharvest_kill crop\n", encoding="utf-8"
    )
    (path / "plants.plt").write_text(
        "plants.plt\n"
        "name lai_pot frac_hu1 lai_max1 frac_hu2 lai_max2 hu_lai_decl can_ht_max rt_dp_max ext_co bm_e\n"
        "corn 6 .15 .15 .5 .95 .8 2.5 2 .65 40\n"
        "grsg 5 .10 .10 .4 .80 .7 2.0 1.5 .55 35\n", encoding="utf-8"
    )


def test_sorghum_workspace_chain_uses_grsg_identifiers_and_only_updates_grsg(tmp_path):
    _sorghum_workspace(tmp_path)
    corn_before = next(line for line in (tmp_path / "plants.plt").read_text(encoding="utf-8").splitlines() if line.startswith("corn "))
    conversion = runner._sorghum(tmp_path)

    assert conversion["landuse"] == "grsg_lum"
    assert conversion["community"] == "grsg_comm"
    assert conversion["rotation"] == "grsg_rot"
    assert "grsg_lum" in (tmp_path / "hru-data.hru").read_text(encoding="utf-8")
    assert "grsg_comm grsg_rot" in (tmp_path / "landuse.lum").read_text(encoding="utf-8")

    manifest = SwatPlantParameterMapper("grsg").apply(tmp_path, _field())
    diagnostic = SwatCropChainDiagnostic.input_chain(tmp_path, [1], crop="grsg")
    after_lines = (tmp_path / "plants.plt").read_text(encoding="utf-8").splitlines()
    corn_after = next(line for line in after_lines if line.startswith("corn "))
    grsg_after = next(line for line in after_lines if line.startswith("grsg "))

    assert manifest["target_hrus"] == ["hru01"]
    assert diagnostic["status"] == "PASS"
    assert all(diagnostic["checks"].values())
    assert corn_after == corn_before
    assert grsg_after != "grsg 5 .10 .10 .4 .80 .7 2.0 1.5 .55 35"


def test_coupled_crop_guard_requires_matching_target_and_proxy_classification():
    runner._require_coupled_field_crop(_field(), "grsg")
    with pytest.raises(ValueError, match="classification"):
        runner._require_coupled_field_crop(_field(fspm_crop="maize"), "grsg")
    with pytest.raises(ValueError, match="target"):
        runner._require_coupled_field_crop(_field(target_plant_name="corn"), "grsg")


def _run_result(run_id, streamflow, *, coupled=False):
    return SimpleNamespace(
        run_id=run_id,
        records=[{
            "period": "2018-01-01", "streamflow_m3s": streamflow, "runoff_mm": 2.0,
            "evapotranspiration_mm": 3.0, "soil_water_mm": 100.0,
        }],
        provenance={
            "output_checksums": {"channel_sd_day.txt": run_id},
            "workspace_modifications": {
                "fspm_parameter_mapping": {"parameter_updates": [{"swat_parameter": "lai_pot"}]}
            } if coupled else {},
            "input_checksum_diff": {"plants.plt": "changed"} if coupled else {},
        },
    )


def test_main_builds_report_with_baseline_reference_totals_without_real_swat(tmp_path, monkeypatch):
    source, root = tmp_path / "source", tmp_path / "repo"
    source.mkdir()
    (root / "research_domain").mkdir(parents=True)
    for name in ("plants.plt", "plant.ini", "landuse.lum", "management.sch", "hru-data.hru", "soils.sol", "time.sim", "print.prt"):
        (source / name).write_text(name, encoding="utf-8")
    executable, cdl = tmp_path / "swatplus", tmp_path / "cdl.parquet"
    executable.write_text("placeholder", encoding="utf-8")
    cdl.write_text("placeholder", encoding="utf-8")
    dataset, schema = tmp_path / "dataset.parquet", tmp_path / "dataset.schema.json"
    dataset.write_text("placeholder", encoding="utf-8")
    schema.write_text("{}", encoding="utf-8")
    baseline, coupled = _run_result("baseline", 1.0), _run_result("coupled", 2.0, coupled=True)
    field = {**_field(fspm_crop="maize", target_plant_name="corn"), "scenario_name": "HISTORICAL_COUPLED_V2"}

    monkeypatch.setattr(runner, "ROOT", root)
    monkeypatch.setattr(runner, "SOURCE_PROJECT", source)
    monkeypatch.setattr(runner, "EXECUTABLE", executable)
    monkeypatch.setattr(runner, "CDL_COMPOSITION", cdl)
    monkeypatch.setattr(runner, "SwatClimateForcingReader", lambda _source: SimpleNamespace(for_period=lambda _start, _end: ([{"temp_c": 20.0}], {"source": "test"})))
    monkeypatch.setattr(runner, "_fspm_field", lambda **_kwargs: (field, {}))
    monkeypatch.setattr(runner, "_run", lambda name, *_args, **_kwargs: baseline if "baseline" in name else coupled)
    monkeypatch.setattr(runner, "_observations", lambda *_args: {"2018-01-01": 1.5})
    monkeypatch.setattr(runner, "ValidationEngine", SimpleNamespace(compare_dated=lambda *_args, **_kwargs: {"alignment": {"matched_dates": ["2018-01-01"]}, "hypothesis_status": "NOT_SUPPORTED"}))
    monkeypatch.setattr(runner, "_run_coupled_scenario", lambda **_kwargs: {"status": "COMPLETED", "comparison_baseline": "HISTORICAL_COUPLED_V2"})
    monkeypatch.setattr(runner, "_write_dataset", lambda *_args: (str(dataset), str(schema)))

    runner.main()

    report = json.loads((root / "research_domain" / "final_report_v2.json").read_text(encoding="utf-8"))
    assert report["baseline"]["totals"]["streamflow_m3s_mean"] == 1.0
    assert report["coupled"]["totals"]["streamflow_m3s_mean"] == 2.0
    assert report["coupling_diagnostic"]["hydrology_delta_from_baseline"]["streamflow_m3s_mean"]["absolute"] == 1.0
    assert report["scenarios"]
