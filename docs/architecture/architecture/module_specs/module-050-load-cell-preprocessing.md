# Module Spec 050: load-cell-data Preprocessing

## Purpose

Open the next bounded `load-cell-data` seam by porting the signal preprocessing helpers that correct impulsive spikes and smooth weight time series.

## Source Inputs

- `load-cell-data/loadcell_pipeline/preprocessing.py`

## Target Outputs

- `src/stomatal_optimiaztion/domains/load_cell/preprocessing.py`
- `src/stomatal_optimiaztion/domains/load_cell/__init__.py`
- `tests/test_load_cell_preprocessing.py`

## Responsibilities

1. preserve impulsive outlier detection, correction, and raw derivative bookkeeping
2. preserve moving-average and Savitzky-Golay smoothing plus derivative reconstruction modes
3. keep the seam preprocessing-bounded without widening into event grouping, workflow, or CLI surfaces

## Non-Goals

- migrate `load-cell-data/loadcell_pipeline/events.py`
- migrate `load-cell-data/loadcell_pipeline/fluxes.py`
- widen into dashboard or workflow entrypoints

## Validation

- `poetry run pytest`
- `poetry run ruff check .`

## Next Seam

- `load-cell-data/loadcell_pipeline/events.py`
