# Module Spec 034: TOMATO tTHORP Shared IO

## Purpose

Open the next bounded TOMATO `tTHORP` seam by porting the shared IO helper layer that creates artifact directories, writes metadata JSON, parses YAML configs, and resolves recursive `extends` chains for downstream pipeline orchestration.

## Source Inputs

- `TOMATO/tTHORP/src/tthorp/core/io.py`

## Target Outputs

- `src/stomatal_optimiaztion/domains/tomato/tomics/alloc/core/`
- `tests/test_tomics_alloc_core_io.py`
- `pyproject.toml`
- `poetry.lock`

## Responsibilities

1. preserve deterministic directory creation and JSON writing behavior for downstream artifact pipelines
2. preserve YAML config parsing, mapping validation, and recursive deep-merge semantics for config inheritance
3. declare `PyYAML` explicitly so config loading works in a clean environment

## Non-Goals

- migrate `TOMATO/tTHORP/src/tthorp/core/scheduler.py`
- migrate `TOMATO/tTHORP/src/tthorp/pipelines/tomato_dayrun.py`
- migrate repo-level `scripts/run_pipeline.py` or `scripts/make_features.py`

## Validation

- `poetry run pytest`
- `poetry run ruff check .`

## Next Seam

- `TOMATO/tTHORP/src/tthorp/core/scheduler.py`
