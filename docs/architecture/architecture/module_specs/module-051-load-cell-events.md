# Module Spec 051: load-cell-data Events

## Purpose

Open the next bounded `load-cell-data` seam by porting the event-detection helpers that convert smoothed derivatives into labeled and merged irrigation or drainage events.

## Source Inputs

- `load-cell-data/loadcell_pipeline/events.py`

## Target Outputs

- `src/stomatal_optimiaztion/domains/load_cell/events.py`
- `src/stomatal_optimiaztion/domains/load_cell/__init__.py`
- `tests/test_load_cell_events.py`

## Responsibilities

1. preserve derivative-based point labeling and hysteresis labeling behavior
2. preserve event grouping, short-event filtering, and close-event merge semantics
3. keep the seam events-bounded without widening into flux decomposition, workflow, or CLI surfaces

## Non-Goals

- migrate `load-cell-data/loadcell_pipeline/fluxes.py`
- migrate workflow orchestration or dashboard entrypoints
- widen into CLI surfaces

## Validation

- `poetry run pytest`
- `poetry run ruff check .`

## Next Seam

- `load-cell-data/loadcell_pipeline/fluxes.py`
