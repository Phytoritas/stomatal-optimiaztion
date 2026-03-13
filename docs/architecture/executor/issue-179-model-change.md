## Why
- `slice 091` restored the TDGM equation registry, so the remaining bounded runtime bridge is `TDGM/src/tdgm/thorp_g_postprocess.py`.
- The postprocess seam closes the current root `TDGM` migration wave by deriving C005 coupling terms from stored THORP-G outputs without re-running THORP.
- The slice should stay bounded to postprocess loaders, synthetic regression coverage, and architecture-status updates without importing external control datasets into the repo.

## Affected model
- `tdgm`
- `src/stomatal_optimiaztion/domains/tdgm/`
- `tests/`
- architecture status docs

## Validation method
- `poetry run pytest`
- `poetry run ruff check .`
- add synthetic coverage for `.mat` loading, forcing-netCDF alignment, helper threshold behavior, and postprocess growth reconstruction

## Comparison target
- legacy `TDGM/src/tdgm/thorp_g_postprocess.py`
- current migrated `src/stomatal_optimiaztion/domains/tdgm/` runtime seams
- root `TDGM` model-card and THORP-G stored-output conventions
