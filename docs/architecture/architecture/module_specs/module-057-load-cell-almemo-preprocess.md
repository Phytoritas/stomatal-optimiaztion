# Module Spec 057: load-cell-data Raw ALMEMO Preprocessing

## Purpose

Open the next bounded `load-cell-data` seam by porting the raw ALMEMO CSV preprocessing module that normalizes channel columns and writes per-day daily CSVs.

## Source Inputs

- `load-cell-data/loadcell_pipeline/almemo_preprocess.py`

## Target Outputs

- `src/stomatal_optimiaztion/domains/load_cell/almemo_preprocess.py`
- `src/stomatal_optimiaztion/domains/load_cell/__init__.py`
- `tests/test_load_cell_almemo_preprocess.py`
- `tests/test_load_cell_run_all.py`

## Responsibilities

1. preserve raw ALMEMO semicolon-CSV parsing, DATE/TIME recovery, and canonical channel mapping
2. preserve duplicate-timestamp merge, optional 1-second interpolation, precision-aware CSV writing, and per-day folder preprocessing
3. reconnect the migrated `run_all` seam to the concrete preprocessing implementation without widening into synthetic validation harnesses

## Non-Goals

- migrate `load-cell-data/loadcell_pipeline/synthetic_test.py`
- widen into dashboard or plotting surfaces
- introduce repo-level wrappers beyond the package-local preprocessing seam

## Validation

- `poetry run pytest`
- `poetry run ruff check .`

## Next Seam

- `load-cell-data/loadcell_pipeline/synthetic_test.py`
