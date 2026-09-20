# Final South Fork Pilot

## Scope

South Fork Iowa River, USGS gauge `05451210`, HUC8 `07080207` is the sole
validation watershed. Multi-watershed validation remains future work; this
implementation performs a reproducible pilot validation on one real
agricultural watershed.

## Reproduction

```bash
cd backend
PYTHONPATH=. SOUTH_FORK_FINAL_RUN_ROOT=/path/to/final-runs \
  .venv/bin/python scripts/run_final_south_fork.py
```

The runner needs the local verified SWAT+ project, executable and CDL parquet
paths described in `research_domain/south_fork_05451210_assessment.json`. It
writes `research_domain/final_report.json` and
`data/final/experiment_dataset.parquet`; it never post-processes SWAT+ output.

## Results

- The numerical results below are the archived `south-fork-final-v1` result
  for the former three-maximum-parameter contract. They are retained as an
  audit record and must not be reported as results of the current v2 contract.
  Run `backend/scripts/run_final_south_fork.py` to create the v2 report with
  parameter-level lineage and input/output checksums.
- Window: 2015--2020; warm-up: 2015--2017; USGS evaluation: 2018--2020.
- Crop diagnostic: 32 CDL corn HRUs resolve to `corn_lum`, `corn_comm`,
  `corn_rot`, auto-management and the `corn` plant record. Output confirms
  35,072 HRU-day records with that active community/rotation.
- Monthly baseline and coupled RMSE: 9.4471 m3/s; NSE: -0.6746; PBIAS:
  -79.58%; KGE: -0.0812; R2: 0.0721.
- Former-contract coupling improvement: 0.0%; conclusion: `H1_NOT_SUPPORTED`.
- `COUPLING_EFFECT = ZERO_WITH_FORMER_PARAMETERIZATION` was accepted after
  verifying active crop configuration and changed `plants.plt` checksums.

## Scenarios

All scenarios were applied to SWAT+ inputs before execution. Values are means
or totals for 2018--2020, relative to the historical baseline.

| Scenario | Streamflow delta | Runoff delta | ET delta | Soil water delta |
| --- | ---: | ---: | ---: | ---: |
| +2 C | -25.93% | -16.39% | +2.60% | -7.93% |
| precipitation -15% | -46.11% | -27.50% | -7.82% | -39.21% |
| no-till (`zerotill`) | -0.00007% | 0.00% | -0.00028% | -0.00022% |
| maize -> grain sorghum (`grsg`) | 0.00% | 0.00% | 0.00% | 0.00% |

Yield is `NOT_AVAILABLE`; no yield proxy is substituted.

## Statistics And Limits

- KS daily observed vs baseline/coupled: D=0.54745,
  asymptotic p=4.46e-143 for both.
- Wilcoxon monthly paired absolute errors: `INSUFFICIENT_EVIDENCE` because all
  pairs are tied. This is a single-watershed temporal comparison, not a
  multi-watershed test.
- Bootstrap SSP5-8.5 yield: `INSUFFICIENT_EVIDENCE`; Sobol:
  `IMPLEMENTED_BUT_NOT_FULLY_EXECUTED`.
- CMIP6 SSP2-4.5 and SSP5-8.5: `NOT_AVAILABLE`, because no normalized
  NEX-GDDP-CMIP6 artifacts were supplied. No synthetic forcing was used.
- NASS validation: `LIMITED` due to county-to-watershed/HRU scale mismatch.
