from pathlib import Path

import pytest

from app.services.swat_plant_parameter_mapper import SwatPlantParameterMapper
from scripts.run_phase35_sensitivity_verification import (
    DIAGNOSTIC_VALUES,
    _compare_output_tables,
    _normalize_days_mat_integer_tokens,
    _normalized_output,
    _parameter_classification,
    _plant_values,
    _set_plant_values,
    _workspace_mutator,
)


BASELINE_PLANTS = {
    "lai_pot": 6.0, "frac_hu1": 0.15, "lai_max1": 0.15, "frac_hu2": 0.5,
    "lai_max2": 0.95, "hu_lai_decl": 0.8, "can_ht_max": 2.5,
    "rt_dp_max": 2.0, "ext_co": 0.65, "bm_e": 40.0,
}


def _plants_file(path: Path) -> Path:
    header = ["name", "days_mat", *SwatPlantParameterMapper.PARAMETER_SPECS, "description"]
    values = ["corn", "120.00000", *(f"{BASELINE_PLANTS[name]:.6f}" for name in SwatPlantParameterMapper.PARAMETER_SPECS), "corn"]
    target = path / "plants.plt"
    target.write_text("plants.plt\n" + " ".join(header) + "\n" + " ".join(values) + "\n", encoding="utf-8")
    return target


def _output(path: Path, rows: list[str]) -> Path:
    target = path / "hru_pw_day.txt"
    target.write_text(
        " SWAT+ synthetic parser fixture\n"
        " jday mon day yr unit gis_id name lai bioms lai_max\n"
        " ---- --- --- -- ---- ------ ---- --- ----- -------\n"
        + "\n".join(rows) + "\n",
        encoding="utf-8",
    )
    return target


def test_oat_value_changes_only_the_named_corn_parameter(tmp_path):
    plants = _plants_file(tmp_path)
    original = _plant_values(plants)

    digest = _set_plant_values(plants, {"lai_pot": DIAGNOSTIC_VALUES["lai_pot"]})

    changed = _plant_values(plants)
    assert digest
    assert {key for key in changed if changed[key] != original[key]} == {"lai_pot"}
    assert changed["lai_pot"] == DIAGNOSTIC_VALUES["lai_pot"]


def test_oat_rejects_out_of_range_and_invalid_curve_order_without_writing(tmp_path):
    plants = _plants_file(tmp_path)
    original = plants.read_bytes()

    with pytest.raises(ValueError, match="outside"):
        _set_plant_values(plants, {"can_ht_max": 20.01})
    with pytest.raises(ValueError, match="LAI curve"):
        _set_plant_values(plants, {"lai_max2": 0.10})

    assert plants.read_bytes() == original


def test_instrumentation_changes_print_controls_but_no_scientific_inputs(tmp_path):
    plants = _plants_file(tmp_path)
    for name in (
        "hru-data.hru", "landuse.lum", "plant.ini", "management.sch", "lum.dtl",
        "file.cio", "time.sim", "weather-sta.cli",
    ):
        (tmp_path / name).write_text(f"{name}\n", encoding="utf-8")
    (tmp_path / "print.prt").write_text(
        "print.prt\n"
        "nyskip day_start yrc_start day_end yrc_end interval\n"
        "0 1 2019 365 2019 1\n"
        "aa_int_cnt\n0\n"
        "csvout use_obj_lbls cdfout\nn n n\n"
        "crop_yld mgtout hydcon fdcout\nb n n n\n"
        "objects daily monthly yearly avann\n"
        "hru_pw n n y y\n",
        encoding="utf-8",
    )
    original_parameters = _plant_values(plants)

    result = _workspace_mutator("BASELINE", BASELINE_PLANTS, BASELINE_PLANTS)(tmp_path)

    assert _plant_values(plants) == original_parameters
    assert result["scientific_inputs_changed"] == []
    assert result["compatibility_normalization"]["numerical_values_changed"] is False
    assert result["diagnostic_control_inputs_changed"] == ["print.prt"]
    print_text = (tmp_path / "print.prt").read_text(encoding="utf-8")
    assert "y             n             n             n" in print_text


def test_numeric_output_comparison_filters_selected_hrus_and_reports_print_precision(tmp_path):
    left = tmp_path / "left"
    right = tmp_path / "right"
    left.mkdir()
    right.mkdir()
    _output(left, [
        "1 1 1 2019 1 1 hru01 0.100 10.000 0.100",
        "1 1 1 2019 2 2 hru02 0.500 20.000 0.500",
    ])
    _output(right, [
        "1 1 1 2019 1 1 hru01 0.120 11.000 0.120",
        "1 1 1 2019 2 2 hru02 0.900 99.000 0.900",
    ])

    result = _compare_output_tables(left / "hru_pw_day.txt", right / "hru_pw_day.txt", [1])

    assert result["normalized_content_equal"] is False
    assert result["comparison_hru_ids"] == [1]
    assert result["variable_differences"]["lai"]["max_absolute_difference"] == pytest.approx(0.02)
    assert result["variable_differences"]["bioms"]["max_absolute_difference"] == pytest.approx(1.0)
    assert result["variable_differences"]["lai"]["first_divergence_date"] == "2019-01-01"
    assert result["print_precision"]["lai"] == 3


def test_equal_numeric_outputs_report_zero_absolute_and_relative_differences(tmp_path):
    left = tmp_path / "left"
    right = tmp_path / "right"
    left.mkdir()
    right.mkdir()
    rows = ["1 1 1 2019 1 1 hru01 0.100 10.000 0.100"]
    _output(left, rows)
    _output(right, rows)

    result = _compare_output_tables(left / "hru_pw_day.txt", right / "hru_pw_day.txt", [1])

    assert result["normalized_content_equal"] is True
    assert result["variable_differences"]["lai"]["changed_records"] == 0
    assert result["variable_differences"]["lai"]["max_absolute_difference"] == 0.0
    assert result["variable_differences"]["lai"]["max_relative_difference"] == 0.0
    assert result["variable_differences"]["lai"]["first_divergence_date"] is None


def test_crop_yield_output_uses_its_real_two_line_header(tmp_path):
    output = tmp_path / "crop_yld_aa.txt"
    output.write_text(
        " basin SWAT+\n"
        "                                      --YIELD (kg/ha)--\n"
        " jday mon day yr unit PLANTNM MASS C N P\n"
        " ---- --- --- -- ---- ------- ---- - - -\n"
        " 365 12 31 2019 1 corn 175.065 78.779 0.263 0.053\n",
        encoding="utf-8",
    )

    table = _normalized_output(output)
    assert table["header"] == ["jday", "mon", "day", "yr", "unit", "PLANTNM", "MASS", "C", "N", "P"]
    assert table["normalized_rows"][0][6] == pytest.approx(175.065)


def test_days_mat_compatibility_rewrites_only_integral_token_representation(tmp_path):
    plants = tmp_path / "plants.plt"
    plants.write_text(
        "plants.plt\nname days_mat lai_pot\ncorn 120.00000 6.00000\nsoyb 0.00000 4.00000\n",
        encoding="utf-8",
    )
    before = plants.read_text(encoding="utf-8")

    result = _normalize_days_mat_integer_tokens(plants)

    after = plants.read_text(encoding="utf-8")
    assert result["rows_normalized"] == 2
    assert result["numerical_values_changed"] is False
    assert before != after
    assert after.splitlines()[2].split() == ["corn", "120", "6.00000"]
    assert after.splitlines()[3].split() == ["soyb", "0", "4.00000"]


def test_days_mat_compatibility_rejects_fractional_values_without_writing(tmp_path):
    plants = tmp_path / "plants.plt"
    plants.write_text("plants.plt\nname days_mat lai_pot\ncorn 120.5 6.00000\n", encoding="utf-8")
    before = plants.read_bytes()

    with pytest.raises(ValueError, match="not an integral value"):
        _normalize_days_mat_integer_tokens(plants)

    assert plants.read_bytes() == before


def test_sensitivity_classification_requires_a_changed_output_or_observable_state(tmp_path):
    run = {
        "workspace": str(tmp_path),
        "plant_status_file": {"status": "AVAILABLE", "headers": ["lai", "bioms", "lai_max"]},
        "management_event_evidence": {"status": "AVAILABLE", "files": [
            {"file": "mgt_out.txt", "corn_management_events": []},
        ]},
    }
    _output(tmp_path, ["1 1 1 2019 1 1 hru01 0.100 10.000 0.100"])
    (tmp_path / "hru_wb_day.txt").write_text(
        "SWAT+\njday mon day yr unit gis_id name eplant perc\n--- --- --- -- ---- ------ ---- ------ ----\n"
        "1 1 1 2019 1 1 hru01 0.2 0.1\n",
        encoding="utf-8",
    )
    unchanged = {"any_normalized_plant_output_change": False, "any_normalized_hydrology_output_change": False}
    changed = {"any_normalized_plant_output_change": True, "any_normalized_hydrology_output_change": False}

    assert _parameter_classification("ext_co", unchanged, run, 1) == "ACTIVE_BUT_NO_DETECTABLE_RESPONSE"
    assert _parameter_classification("can_ht_max", unchanged, run, 1) == "OUTPUT_NOT_OBSERVABLE"
    assert _parameter_classification("can_ht_max", changed, run, 1) == "ACTIVE_AND_SENSITIVE"
    assert _parameter_classification("lai_pot", unchanged, run, 0) == "LIKELY_NOT_ACTIVE"

    run["plant_status_file"] = {"status": "NOT_AVAILABLE", "headers": []}
    assert _parameter_classification("lai_pot", unchanged, run, 0) == "OUTPUT_NOT_OBSERVABLE"
