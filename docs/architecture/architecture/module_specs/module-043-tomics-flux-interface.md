# Module Spec 043: TOMATO tGOSM Interface

## Purpose

Open the next bounded TOMATO seam by porting the `tGOSM` interface surface that exposes the placeholder stomatal optimization function on top of the migrated contracts.

## Source Inputs

- `TOMATO/tGOSM/src/tgosm/interface.py`
- `TOMATO/tGOSM/tests/test_tgosm_contracts.py`

## Target Outputs

- `src/stomatal_optimiaztion/domains/tomato/tomics/flux/interface.py`
- `src/stomatal_optimiaztion/domains/tomato/tomics/flux/__init__.py`
- `tests/test_tomics_flux_interface.py`

## Responsibilities

1. preserve the placeholder optimizer behavior that maps water-supply stress to a nonnegative conductance target
2. preserve explicit `lambda_wue` and `objective_value` placeholders in the returned result
3. expose the interface through the staged `tgosm` package without widening into non-placeholder optimizer dependencies

## Non-Goals

- migrate `TOMATO/tTDGM/src/ttdgm/contracts.py`
- introduce a wider stomatal optimization backend
- widen into cross-model shared abstractions

## Validation

- `poetry run pytest`
- `poetry run ruff check .`

## Next Seam

- `TOMATO/tTDGM/src/ttdgm/contracts.py`
