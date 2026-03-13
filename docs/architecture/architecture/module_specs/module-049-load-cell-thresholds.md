# Module Spec 049: load-cell-data Thresholds

## Purpose

Open the next bounded `load-cell-data` seam by porting the adaptive threshold detector that converts smoothed derivatives into irrigation and drainage thresholds.

## Source Inputs

- `load-cell-data/loadcell_pipeline/thresholds.py`

## Target Outputs

- `src/stomatal_optimiaztion/domains/load_cell/thresholds.py`
- `src/stomatal_optimiaztion/domains/load_cell/__init__.py`
- `tests/test_load_cell_thresholds.py`

## Responsibilities

1. preserve robust baseline and sigma estimation from the derivative distribution
2. preserve valid-mask fallback behavior plus physical sign constraints on irrigation and drainage thresholds
3. keep the seam threshold-bounded without widening into preprocessing, workflow, or CLI surfaces

## Non-Goals

- migrate `load-cell-data/loadcell_pipeline/preprocessing.py`
- migrate event-labeling or workflow orchestration
- widen into dashboard entrypoints

## Validation

- `poetry run pytest`
- `poetry run ruff check .`

## Next Seam

- `load-cell-data/loadcell_pipeline/preprocessing.py`
