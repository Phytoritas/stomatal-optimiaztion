# Module Spec 056: load-cell-data End-to-End Runner

## Purpose

Open the next bounded `load-cell-data` seam by porting the top-level runner that composes raw preprocessing with workflow or sweep execution.

## Source Inputs

- `load-cell-data/loadcell_pipeline/run_all.py`

## Target Outputs

- `src/stomatal_optimiaztion/domains/load_cell/run_all.py`
- `src/stomatal_optimiaztion/domains/load_cell/__init__.py`
- `tests/test_load_cell_run_all.py`

## Responsibilities

1. preserve CLI parser construction and end-to-end orchestration across preprocessing plus workflow-or-sweep dispatch
2. preserve the dual daily-output preprocessing contract for raw and 1-second-interpolated CSV directories
3. keep the seam bounded by lazily resolving or injecting raw preprocessing until `almemo_preprocess.py` is migrated

## Non-Goals

- migrate `load-cell-data/loadcell_pipeline/almemo_preprocess.py`
- widen into dashboard or reporting surfaces
- introduce repo-level wrappers beyond the package-local runner seam

## Validation

- `poetry run pytest`
- `poetry run ruff check .`

## Next Seam

- `load-cell-data/loadcell_pipeline/almemo_preprocess.py`
