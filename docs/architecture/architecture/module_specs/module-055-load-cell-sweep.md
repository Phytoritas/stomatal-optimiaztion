# Module Spec 055: load-cell-data Sweep

## Purpose

Open the next bounded `load-cell-data` seam by porting the parameter-sweep runner that generates config variants, dispatches batch workflows, and ranks resulting runs.

## Source Inputs

- `load-cell-data/loadcell_pipeline/sweep.py`

## Target Outputs

- `src/stomatal_optimiaztion/domains/load_cell/sweep.py`
- `src/stomatal_optimiaztion/domains/load_cell/__init__.py`
- `tests/test_load_cell_sweep.py`

## Responsibilities

1. preserve grid parsing, generated config validation, and YAML/config CSV emission
2. preserve workflow dispatch, run collection, and per-variant ranking outputs
3. keep the seam sweep-bounded without widening into raw preprocessing or end-to-end runner surfaces

## Non-Goals

- migrate `load-cell-data/loadcell_pipeline/run_all.py`
- widen into raw ALMEMO preprocessing
- widen into dashboard surfaces

## Validation

- `poetry run pytest`
- `poetry run ruff check .`

## Next Seam

- `load-cell-data/loadcell_pipeline/run_all.py`
