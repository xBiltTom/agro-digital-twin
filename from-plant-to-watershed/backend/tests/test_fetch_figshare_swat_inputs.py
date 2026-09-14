import importlib.util
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "scripts" / "fetch_figshare_swat_inputs.py"
spec = importlib.util.spec_from_file_location("figshare_fetch", SCRIPT)
module = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(module)


def test_input_filter_never_accepts_preexisting_swat_outputs():
    prefix = module.BOONE_CDL_PREFIX
    assert module._is_input_member(prefix + "plants.plt", prefix)
    assert module._is_input_member(prefix + "weather-sta.cli", prefix)
    assert not module._is_input_member(prefix + "channel_sd_day.txt", prefix)
    assert not module._is_input_member(prefix + "hru_wb_yr.txt", prefix)
    assert not module._is_input_member(prefix + "checker.out", prefix)
    assert not module._is_input_member(prefix + "success.fin", prefix)
    assert not module._is_input_member(prefix + "hru_cflux_stat.txt", prefix)


def test_member_path_is_confined_to_requested_txtinout_root(tmp_path):
    assert module._safe_relative(module.BOONE_CDL_PREFIX + "nested/input.cli", module.BOONE_CDL_PREFIX) == Path("nested/input.cli")
    try:
        module._safe_relative(module.BOONE_CDL_PREFIX + "../escape", module.BOONE_CDL_PREFIX)
    except RuntimeError as exc:
        assert "unsafe" in str(exc)
    else:
        raise AssertionError("path traversal must be rejected")
