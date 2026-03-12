# Module Spec 018: THORP Load Forcing

## Purpose

Migrate the bounded `load_forcing` seam so the new package can ingest THORP forcing inputs without pulling simulation orchestration into the forcing boundary.

## Source Inputs

- `THORP/src/thorp/forcing.py` (`Forcing`, `load_forcing`)
- migrated `THORPParams` compatibility bundle in `src/stomatal_optimiaztion/domains/thorp/params.py`

## Target Outputs

- `src/stomatal_optimiaztion/domains/thorp/forcing.py`
- `tests/test_thorp_forcing.py`

## Responsibilities

1. preserve legacy forcing matrix shape normalization for both `n x 6` and `6 x n` netCDF layouts
2. preserve clipping, truncation, repetition, and scaling behavior for the forcing series
3. reconstruct solar-angle forcing from migrated parameter metadata without reaching into the simulation loop

## Non-Goals

- port `SimulationOutputs` from `simulate.py`
- port `_Store`, `simulate`, or MAT-file export
- depend on workspace-global forcing files during tests

## Validation

- `poetry run pytest`
- `poetry run ruff check .`

## Next Seam

- `SimulationOutputs` from `simulate.py`
