## Why
- `slice 057` migrated the raw ALMEMO preprocessing seam, so the next remaining bounded `load-cell-data` surface inside `loadcell_pipeline/` is the synthetic validation harness at `synthetic_test.py`.
- The migrated repo now has the full processing pipeline, but it still lacks the legacy synthetic dataset generator and end-to-end mass-balance validation helper that exercises the pipeline without external files.
- This slice should stay validation-harness-bounded: synthetic timeseries generation, pipeline execution against `run_pipeline`, tolerance checks, and package-local export only.

## Affected model
- `load-cell-data`
- `src/stomatal_optimiaztion/domains/load_cell/`
- related load-cell synthetic harness tests and package exports

## Validation method
- `poetry run pytest`
- `poetry run ruff check .`
- add coverage for deterministic synthetic dataset generation, truth totals, end-to-end synthetic pipeline validation, and package import surface

## Comparison target
- legacy `load-cell-data/loadcell_pipeline/synthetic_test.py`
- current migrated `src/stomatal_optimiaztion/domains/load_cell/{cli.py,config.py}`
