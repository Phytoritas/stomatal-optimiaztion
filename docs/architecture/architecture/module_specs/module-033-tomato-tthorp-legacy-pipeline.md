# Module Spec 033: TOMATO tTHORP Package-Level Legacy Pipeline

## Purpose

Open the next bounded TOMATO `tTHORP` seam by porting the package-level legacy pipeline wrapper that resolves repo-relative paths, builds the default migrated tomato model, runs the tabular simulation, and summarizes output metrics.

## Source Inputs

- `TOMATO/tTHORP/src/tthorp/pipelines/tomato_legacy.py`

## Target Outputs

- `src/stomatal_optimiaztion/domains/tomato/tthorp/pipelines/`
- `tests/test_tomato_tthorp_pipeline.py`

## Responsibilities

1. preserve repo-root and forcing-path resolution behavior for config-driven pipeline runs
2. preserve the bounded execution order across `iter_forcing_csv()`, `make_tomato_legacy_model()`, and `simulate()`
3. preserve package-local config payload filtering and summary-metric helpers without reopening the legacy `core/` layer

## Non-Goals

- migrate `TOMATO/tTHORP/src/tthorp/core/io.py`
- migrate `TOMATO/tTHORP/src/tthorp/core/scheduler.py`
- migrate `TOMATO/tTHORP/src/tthorp/pipelines/tomato_dayrun.py`

## Validation

- `poetry run pytest`
- `poetry run ruff check .`

## Next Seam

- `TOMATO/tTHORP/src/tthorp/core/io.py`
