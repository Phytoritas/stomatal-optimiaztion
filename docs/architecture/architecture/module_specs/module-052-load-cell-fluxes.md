# Module Spec 052: load-cell-data Fluxes

## Purpose

Open the next bounded `load-cell-data` seam by porting the flux-decomposition helper that converts labeled derivatives into irrigation, drainage, and transpiration fluxes.

## Source Inputs

- `load-cell-data/loadcell_pipeline/fluxes.py`

## Target Outputs

- `src/stomatal_optimiaztion/domains/load_cell/fluxes.py`
- `src/stomatal_optimiaztion/domains/load_cell/__init__.py`
- `tests/test_load_cell_fluxes.py`

## Responsibilities

1. preserve per-second irrigation, drainage, and transpiration decomposition from smoothed derivatives and labels
2. preserve optional transpiration interpolation during non-baseline segments plus cumulative-sum reporting
3. keep the seam flux-bounded without widening into pipeline orchestration, workflow, or CLI surfaces

## Non-Goals

- migrate `load-cell-data/loadcell_pipeline/cli.py`
- migrate workflow orchestration or batch-runner entrypoints
- widen into dashboard surfaces

## Validation

- `poetry run pytest`
- `poetry run ruff check .`

## Next Seam

- `load-cell-data/loadcell_pipeline/cli.py`
