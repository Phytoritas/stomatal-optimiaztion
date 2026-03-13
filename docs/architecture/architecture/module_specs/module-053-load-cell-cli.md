# Module Spec 053: load-cell-data CLI

## Purpose

Open the next bounded `load-cell-data` seam by porting the package-level pipeline CLI that ties config loading, migrated helpers, and multi-resolution output writing together.

## Source Inputs

- `load-cell-data/loadcell_pipeline/cli.py`

## Target Outputs

- `src/stomatal_optimiaztion/domains/load_cell/cli.py`
- `src/stomatal_optimiaztion/domains/load_cell/__init__.py`
- `tests/test_load_cell_cli.py`

## Responsibilities

1. preserve parser construction and CLI-to-config override mapping
2. preserve package-level pipeline orchestration, event timing fields, summary stats, and multi-resolution output writing
3. keep the seam CLI-bounded without widening into batch workflow, sweep, or dashboard surfaces

## Non-Goals

- migrate `load-cell-data/loadcell_pipeline/workflow.py`
- migrate batch-runner or sweep entrypoints
- widen into dashboard surfaces

## Validation

- `poetry run pytest`
- `poetry run ruff check .`

## Next Seam

- `load-cell-data/loadcell_pipeline/workflow.py`
