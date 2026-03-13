# Module Spec 054: load-cell-data Workflow

## Purpose

Open the next bounded `load-cell-data` seam by porting the batch workflow runner that organizes per-day environment exports and per-config result trees across raw and interpolated variants.

## Source Inputs

- `load-cell-data/loadcell_pipeline/workflow.py`

## Target Outputs

- `src/stomatal_optimiaztion/domains/load_cell/workflow.py`
- `src/stomatal_optimiaztion/domains/load_cell/__init__.py`
- `tests/test_load_cell_workflow.py`

## Responsibilities

1. preserve stable config signatures, filename matching, and weight-column inference across canonical and legacy daily CSVs
2. preserve daily environment export, substrate-sensor joins, and per-config/per-loadcell result-tree writing
3. keep the seam workflow-bounded without widening into sweep, raw preprocessing, or end-to-end batch entrypoints

## Non-Goals

- migrate `load-cell-data/loadcell_pipeline/sweep.py`
- migrate `load-cell-data/loadcell_pipeline/run_all.py`
- widen into raw ALMEMO preprocessing

## Validation

- `poetry run pytest`
- `poetry run ruff check .`

## Next Seam

- `load-cell-data/loadcell_pipeline/sweep.py`
