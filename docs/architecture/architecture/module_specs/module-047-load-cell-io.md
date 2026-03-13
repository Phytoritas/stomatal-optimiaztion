# Module Spec 047: load-cell-data IO

## Purpose

Open the next bounded `load-cell-data` seam by porting the ingestion and result-writing helper surface that reads raw CSV data and persists processed artifacts.

## Source Inputs

- `load-cell-data/loadcell_pipeline/io.py`

## Target Outputs

- `src/stomatal_optimiaztion/domains/load_cell/io.py`
- `src/stomatal_optimiaztion/domains/load_cell/__init__.py`
- `tests/test_load_cell_io.py`

## Responsibilities

1. preserve raw load-cell CSV ingestion, duplicate-timestamp handling, interpolation flags, and 1-second reindexing behavior
2. preserve CSV artifact writing for single-resolution and multi-resolution outputs
3. keep optional Excel export behavior explicit without widening into workflow or preprocessing seams

## Non-Goals

- migrate `load-cell-data/loadcell_pipeline/aggregation.py`
- migrate `load-cell-data/loadcell_pipeline/preprocessing.py`
- widen into CLI, workflow, or dashboard entrypoints

## Validation

- `poetry run pytest`
- `poetry run ruff check .`

## Next Seam

- `load-cell-data/loadcell_pipeline/aggregation.py`
