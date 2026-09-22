# FSPM → SWAT+ one-way coupled experiment

`SWAT_STANDARD_BASELINE` remains an untouched SWAT+ crop configuration. A request
for `SWAT_MULTISCALE_COUPLED` creates a baseline sibling and a coupled sibling with
one `experiment_id`; both use the same source project, dates, forcing and initial
conditions. The only coupled write occurs after the source project is copied into
the coupled workspace.

The crop layer is a deterministic `SIMPLIFIED_FSPM`, not a complete botanical
FSPM. It evaluates 1,000 parameter-varying representative plants, derives an
annual thermal-time/LAI trajectory for each crop season, and aggregates the
seasonal contracts. `SwatClimateForcingReader` reads the selected SWAT+
station precipitation and temperature records; where the reference uses WGN for
solar/humidity, the FSPM records that limitation instead of presenting a second
observed forcing source.

## Seasonal clock (v2.1)

South Fork's source `management.sch` invokes `pl_hv_summer1`; `lum.dtl` configures
that decision table with `phu_base0 > 0.15`, a soil-water condition, and a fixed
harvest fallback at day 350. The TxtInOut and selected print outputs do not expose
the executed planting event. Consequently the FSPM does **not** reset at January
1: it opens an `APPROXIMATE_PLANTING_WINDOW` when PHU accumulated above the
`phu_base0` reference temperature (0 °C) reaches `0.15 × thermal_maturity_gdd`,
then resets crop GDD and absorbed PAR only at that window start and closes at the
configured harvest boundary. `plants.plt.tmp_base` remains the FSPM crop-growth
base temperature and is used directly for each FSPM growth-GDD increment
(`fspm_growth_temperature_base_c`, source `plants.plt.tmp_base`); it is not a
replacement for SWAT+'s `phu_base0` trigger. Provenance records the
decision table, source files, trigger, dates/windows, confidence `LIMITED`, and
the fact that only the pre-plant annual PHU accumulator resets at the calendar
boundary (never the FSPM season). This is an explicit approximation, not a claim that
SWAT+ planted on that date.

The window uses only the configured `phu_base0` threshold and `jday` harvest
boundary. `dynamic_conditions_not_reproduced` records all additional decision-table
conditions (for South Fork: the PHU fallback threshold, `phu_plant`, `soil_water`,
and `year_rot`). They require SWAT+'s internal HRU/crop state or an executed-event
trace and are deliberately not emulated. Therefore an approximate window is never
reported as SWAT+'s executed planting date.

`ext_co` and `bm_e` originate as model-base assumptions, with seeded bounded
intra-population variation. Until a repository artifact supports calibration,
their provenance is `ASSUMED_PARAMETER_NOT_CALIBRATED`, `calibrated: false`, and
records source value, population mean/std, model clamp and SWAT+ documented range.
They are not inferred or discovered from the 1,000 plants.

## Coupled scenario contract (v2.1.1 correction)

`HISTORICAL_COUPLED_V2` is the reference for scenario deltas. The scientific H1
comparison remains separate: `SWAT_STANDARD_BASELINE` versus
`SWAT_MULTISCALE_COUPLED`. Climate scenarios perturb the FSPM forcing first,
re-run the seeded 1,000-plant population, and then map that scenario-specific
field to a coupled SWAT+ workspace. The precipitation scenario records that the
simplified FSPM still has fixed `soil_moisture_vol=0.24`; it does not fabricate
a root-zone water response from rainfall until that state is defensibly modeled.
`NO_TILL` instead reuses the historical
coupled field and records `FSPM_RESPONSE_TO_MANAGEMENT=NOT_MODELED`, because no
direct no-till physiology is represented. `MAIZE_TO_SORGHUM` runs only the
explicit `SIMPLIFIED_SORGHUM_PROXY` and maps it to `grsg`; a maize field is
rejected for that crop mapping.

`SwatPlantParameterMapper` changes only the active crop record in `plants.plt`.
The source project's real `plants.plt` header is checked before every write; the
field meanings/ranges follow the [SWAT+ plants.plt input documentation](https://swatplus.gitbook.io/io-docs/introduction-1/databases/plants.plt)
and its [canopy/thermal-time equations](https://swatplus.gitbook.io/io-docs/theoretical-documentation/section-5-land-cover-plant/optimal-growth/potential-growth/canopy-cover-and-height).

| Field aggregate | SWAT+ parameter | Units |
| --- | --- | --- |
| seasonal peak `mean_LAI` | `lai_pot` | m² leaf / m² ground |
| FSPM LAI development at 15%/85% of peak | `frac_hu1`, `lai_max1`, `frac_hu2`, `lai_max2` | fraction of heat units / peak LAI |
| first post-peak green-LAI decline | `hu_lai_decl` | fraction of heat units |
| `plant_height_mean_m` | `can_ht_max` | m |
| `root_depth_mean_m` | `rt_dp_max` | m, capped by the referenced `soils.sol` `zmx` or `dp_tot` when available |
| Beer--Lambert canopy coefficient used in FSPM cover | `ext_co` | dimensionless |
| mean population radiation-use efficiency | `bm_e` | kg ha⁻¹ /(MJ m⁻²) |

Each mapping logs FSPM value, SWAT original/coupled value, absolute/percent
delta, unit, clamp, HRU crop scope, input file and rationale. The adapter records
checksums before and after the mutator for `plants.plt`, `plant.ini`, land-use,
management, HRU, soil and control inputs. Actual/potential ET, soil-water uptake,
stress, stomatal conductance, root distribution and yield are explicitly
`NOT_COUPLED`: SWAT+ computes hydrology internally, and no unit-valid conversion
to an appropriate plant input was demonstrated here. No post-execution output
adjustment is permitted.

The old coupling was weak because it changed just three maxima in a static plant
record, while SWAT+ uses a heat-unit LAI curve, radiation interception and biomass
growth during each planted season. A changed input checksum alone did not prove
that those maxima were dynamically limiting the active HRUs.

## Phase 1 plant-water unit correction (proposed v3 execution)

The existing South Fork v2 report and dataset are historical outputs. They were
computed with `soil_moisture_vol=0.24` at the FSPM entry point, while the
`SimplifiedPlantModel` uses volumetric **percent** thresholds of 12, 32 and 44.
Thus the model interpreted an intended volumetric fraction of 0.24 (24%) as
0.24%. The population also divided a seeded moisture offset, already measured
in percentage points, by 100. Both errors have been corrected in source code;
the v2 metrics and conclusions have not been changed.

| Component | Water variable | Unit and meaning |
| --- | --- | --- |
| SWAT+ output parser | `soil_water_mm` | mm of soil-water storage over its modeled soil profile; kept separate |
| South Fork FSPM source | assumed `0.24` fraction | converted once to 24 volumetric percent; constant for all days |
| `SimplifiedPlantModel`, `PlantPopulation`, field aggregate and proxy HRU | `soil_moisture_vol` | volumetric percent in [0, 100] |
| Plant heterogeneity | `soil_moisture_offset` | volumetric percentage points (sampled within ±3) |
| Simplified hydrology | `soil_water_depth_mm` and `soil_moisture_vol` | mm and percent respectively; its assumed 1000 mm profile yields `mm / profile_mm × 100` |

The 1000 mm profile in the separate simplified hydrology model is **not** a
valid conversion factor for SWAT+ HRU soil water. SWAT+ soil storage can cover
different soil depths/layers and spatial supports. A defensible HRU/root-zone
profile mapping and time alignment are still required before SWAT+ `soil_water_mm`
can drive FSPM moisture. The corrected South Fork FSPM continues to use an
explicitly tagged assumed constant; its precipitation scenarios still have no
modeled soil-moisture response. The SWAT+ crop mapper remains one-way and does
not write FSPM ET, uptake or stress into SWAT+.

The fixed-weather FSPM response changes under this correction: stress and
actual transpiration/uptake change, while potential transpiration does not.
LAI and instantaneous biomass estimates depend on stress; canopy interception
can then change cumulative absorbed PAR and later biomass. Root depth and
phenology do not depend on moisture in this simplified model. Biomass is an
algebraic estimate from cumulative intercepted radiation and current stress;
it is not a validated daily carbon balance. Sap flow is a proxy proportional
to actual transpiration and is zero at zero flux. None of these variables is
an observed or fully validated 3D plant state.

`run_final_south_fork.py` now writes `final_report_v3.json` and
`experiment_dataset_v3.parquet` if deliberately executed. It leaves the v2
artifacts and the current report API pointer unchanged. A v3 execution must be
reviewed with its own provenance and observational validation before any claim
of improved FSPM–SWAT+ coupling or promotion as the current result.

For a read-only comparison using the same 2015–2020 SWAT+ weather files,
seed 42, 1,000 plants and historical `final_report_v2.json`, call
`scripts.run_final_south_fork._fspm_field()` from the backend and compare its
field aggregate with `report["fspm"]["field_aggregate"]`. The population's
peak-canopy field changes as follows (these are FSPM outputs, not new SWAT+
results):

```bash
cd backend
./.venv/bin/python - <<'PY'
import json
from pathlib import Path
from scripts.run_final_south_fork import _fspm_field

old = json.loads(Path('../research_domain/final_report_v2.json').read_text())['fspm']['field_aggregate']
new, _ = _fspm_field()
for key in ('soil_moisture_vol', 'mean_LAI', 'potential_ET_mm_day',
            'actual_ET_mm_day', 'water_stress', 'biomass_g_plant'):
    print(key, old[key], new[key])
PY
```

Set `SOUTH_FORK_SWAT_PROJECT` to the original project's `TxtInOut` if its local
path differs from the runner default. This command reads inputs and does not
write a new report.

| Variable | Historical v2 | Corrected code, same forcing |
| --- | ---: | ---: |
| Assumed soil moisture (% volumetric) | 0.24 | 24.0 |
| Mean LAI | 2.821900386 | 5.004551569 |
| Potential ET (mm/day) | 2.476320524 | 2.476320524 |
| Actual ET / uptake (mm/day) | 0 | 2.340662154 |
| Mean water stress | 1 | 0.05448651 |
| Biomass estimate (g/plant) | 128.885444 | 260.853183 |

The biomass difference includes changed canopy interception during the season;
the two peak states need not fall on the same day. These values do not establish
improved runoff or streamflow prediction.
