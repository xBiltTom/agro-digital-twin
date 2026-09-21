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
