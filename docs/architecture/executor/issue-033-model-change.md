## Why
- `slice 032` closed the TOMATO partitioning package, so the next bounded seam is the package-level legacy pipeline wrapper at `pipelines/tomato_legacy.py`.
- The migrated repo still lacks a config-driven surface that resolves repo-relative forcing paths, constructs the default tomato pipeline model, and summarizes output metrics without reopening `core/` helpers.

## Affected model
- `TOMATO tTHORP`
- `src/stomatal_optimiaztion/domains/tomato/tthorp/pipelines/`
- related TOMATO pipeline integration tests and architecture slice records

## Validation method
- `poetry run pytest`
- `poetry run ruff check .`
- add path-resolution, pipeline-run, and metrics-summary coverage over the migrated `simulate`, `iter_forcing_csv`, and `make_tomato_legacy_model` seams

## Comparison target
- legacy `TOMATO/tTHORP/src/tthorp/pipelines/tomato_legacy.py`
- current migrated TOMATO `interface`, `forcing_csv`, adapter, runner, and partition-policy seams
