# SWAT+ baseline: real integration evidence

This repository does not distribute a SWAT+ binary or input project. The
integration test uses the official sources at execution time and never treats
the following reference project as the research-domain watershed.

## Verified reference run

- Engine: official `swat-model/swatplus` Linux x86_64 release `62.0.0`.
- Release archive SHA-256:
  `d0244e0ef07289ccb0fcf1a69bfef53ffb16f7dbc464b827f0143f26bde333f9`.
- Extracted executable SHA-256:
  `5d30a2d255f6c0d49e8456835523156b85b0d204334bd27d8f461994bacbe8b6`.
- Input project: official `refdata/Osu_1hru` (one HRU, 10 ha) from
  `https://github.com/swat-model/swatplus.git`, commit
  `cb442f7c05fc3bfc34349c446010f452d2737ca0`.
- Deterministic project-tree manifest SHA-256:
  `6c4a3f7a371302b5e5432b213c2e6894b976295ba210407b79faf6e7a2175f4a`.

The run used `2010-01-01` through `2010-12-31`, selected from the input
project's own supported range, with daily outputs and zero warm-up years. It is
not a fixed value in application code.

## Reproduce

Download the archive listed in the official SWAT+ release page, extract it, and
clone the cited revision of the source repository. Then run the real API test:

```bash
SWAT_PLUS_EXECUTABLE=/absolute/path/swatplus-62.0.0-gnu-lin_x86_64-Rel \
SWAT_PLUS_PROJECT_DIR=/absolute/path/swatplus/refdata/Osu_1hru \
SWAT_PLUS_WORKING_DIRECTORY=/tmp/swat-api-real-workspaces \
SWAT_PLUS_INTEGRATION_START=2010-01-01 \
SWAT_PLUS_INTEGRATION_END=2010-12-31 \
SWAT_PLUS_INTEGRATION_OUTPUT_FREQUENCY=DAILY \
pytest -q backend/tests/test_swat_plus_adapter.py -m integration
```

`SwatPlusAdapter` copies the source folder first. In that workspace it updates
the data row of `time.sim`, updates the print window and selected
`basin_wb`/`hru_wb`/`channel`/`channel_sd` output frequency in `print.prt`, and
removes every parser-supported stale output before calling SWAT+. Provenance
records both configured file checksums and each output checksum/mtime after the
process start.
