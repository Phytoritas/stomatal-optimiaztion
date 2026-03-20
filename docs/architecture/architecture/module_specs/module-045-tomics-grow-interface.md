# Module Spec 045: TOMATO tTDGM Interface

## Purpose

Open the next bounded TOMATO seam by porting the `tTDGM` interface surface that exposes the placeholder growth-step function on top of the migrated contracts.

## Source Inputs

- `TOMATO/tTDGM/src/ttdgm/interface.py`
- `TOMATO/tTDGM/tests/test_ttdgm_contracts.py`

## Target Outputs

- `src/stomatal_optimiaztion/domains/tomato/tomics/grow/interface.py`
- `src/stomatal_optimiaztion/domains/tomato/tomics/grow/__init__.py`
- `tests/test_tomics_grow_interface.py`

## Responsibilities

1. preserve the placeholder growth-step behavior that validates allocations and returns explicit zeroed organ growth channels
2. preserve the pool passthrough semantics for the returned `GrowthStepOutput`
3. expose the interface through the staged `ttdgm` package without widening into new physiology or shared abstractions

## Non-Goals

- migrate `load-cell-data/loadcell_pipeline/config.py`
- introduce non-placeholder `tTDGM` growth behavior
- widen into cross-domain shared abstractions

## Validation

- `poetry run pytest`
- `poetry run ruff check .`

## Next Seam

- `load-cell-data/loadcell_pipeline/config.py`
