# Module Spec 036: TOMATO tTHORP Dayrun Pipeline

## Purpose

Open the next bounded TOMATO `tTHORP` seam by porting the dayrun pipeline wrapper that executes the migrated legacy pipeline against config payloads and writes deterministic run artifacts.

## Source Inputs

- `TOMATO/tTHORP/src/tthorp/pipelines/tomato_dayrun.py`

## Target Outputs

- `src/stomatal_optimiaztion/domains/tomato/tthorp/pipelines/`
- `tests/test_tomato_tthorp_dayrun.py`

## Responsibilities

1. preserve config-driven execution over migrated `core/io`, `core/scheduler`, and `tomato_legacy` seams
2. preserve deterministic `df.csv` and `meta.json` artifact writing with stable metadata fields
3. preserve package-level from-config execution so repo-level scripts can target one migrated dayrun surface

## Non-Goals

- migrate repo-level `scripts/run_pipeline.py`
- migrate repo-level `scripts/make_features.py`
- broaden into workspace-wide CLI entrypoints

## Validation

- `poetry run pytest`
- `poetry run ruff check .`

## Next Seam

- `TOMATO/tTHORP/scripts/run_pipeline.py`
