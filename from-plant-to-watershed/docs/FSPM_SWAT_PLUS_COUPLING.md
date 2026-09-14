# FSPM → SWAT+ one-way coupled experiment

`SWAT_STANDARD_BASELINE` remains an untouched SWAT+ crop configuration. A request
for `SWAT_MULTISCALE_COUPLED` creates a baseline sibling and a coupled sibling with
one `experiment_id`; both use the same source project, dates, forcing and initial
conditions. The only coupled write occurs after the source project is copied into
the coupled workspace.

The maize FSPM is deterministic for its seed, weather input, soil-state assumption
and parameters. It evaluates 1,000 parameter-varying plants, then aggregates the
seasonal peak canopy state. `SwatClimateForcingReader` reads the selected SWAT+
station precipitation and temperature records; where the reference uses WGN for
solar/humidity, the FSPM records that limitation instead of presenting a second
observed forcing source.

`SwatPlantParameterMapper` changes only the active crop record in `plants.plt`:

| Field aggregate | SWAT+ parameter | Units |
| --- | --- | --- |
| `mean_LAI` | `lai_pot` | m² leaf / m² ground |
| `plant_height_mean_m` | `can_ht_max` | m |
| `root_depth_mean_m` | `rt_dp_max` | m, capped by `soils.sol` `ZMX` when available |

The manifest persists each original and coupled value, input file, HRU scope,
transformation, unit and rationale. Actual ET, soil-water uptake and yield are
explicitly `NOT_COUPLED`: SWAT+ recalculates them from the modified inputs. No
post-execution output adjustment is permitted.
