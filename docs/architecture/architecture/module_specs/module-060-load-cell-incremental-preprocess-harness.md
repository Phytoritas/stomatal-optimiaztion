# Module Spec 060: load-cell-data Incremental Preprocess Harness

## Purpose

Open the next bounded `load-cell-data` seam by porting the repo-level incremental preprocess harness that upserts canonical parquet artifacts and refreshes preprocess-compare viewer cache data.

## Source Inputs

- `load-cell-data/src/preprocess_incremental.py`

## Target Outputs

- `scripts/preprocess_incremental.py`
- `tests/test_load_cell_preprocess_incremental_script.py`
- `pyproject.toml`
- `poetry.lock`

## Responsibilities

1. preserve marker-backed incremental raw-file skip logic
2. preserve daily canonical parquet upsert and transpiration parquet emission
3. preserve optional viewer JSON cache refresh while keeping the seam repo-level and bounded

## Non-Goals

- migrate `load-cell-data/src/preprocess_compare_server.py`
- migrate `load-cell-data/src/build_preprocess_compare_viewer.py`
- redesign preprocess-compare viewer payloads or export flows

## Validation

- `poetry run pytest`
- `poetry run ruff check .`

## Next Seam

- `load-cell-data/src/preprocess_compare_server.py`
