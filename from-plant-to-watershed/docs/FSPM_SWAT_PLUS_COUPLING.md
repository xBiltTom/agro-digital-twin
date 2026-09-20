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
