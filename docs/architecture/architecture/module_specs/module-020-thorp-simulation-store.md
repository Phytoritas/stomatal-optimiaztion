# Module Spec 020: THORP Simulation Store

## Purpose

Migrate the bounded `_Store` seam so the new package can buffer THORP simulation outputs and emit `SimulationOutputs` without porting the full simulation loop.

## Source Inputs

- `THORP/src/thorp/simulate.py` (`_Store`)
- migrated `SimulationOutputs` in `src/stomatal_optimiaztion/domains/thorp/simulation.py`
- migrated `THORPParams` compatibility bundle in `src/stomatal_optimiaztion/domains/thorp/params.py`

## Target Outputs

- `src/stomatal_optimiaztion/domains/thorp/simulation.py`
- `tests/test_thorp_simulation_store.py`

## Responsibilities

1. preserve legacy buffering and cadence rules for stored simulation checkpoints
2. preserve the conversion from buffered lists into `SimulationOutputs`
3. keep MAT export behind an injected callback so orchestration and export can migrate later

## Non-Goals

- port `_initial_allometry` from `simulate.py`
- port `run` or CLI entrypoints
- port the MATLAB writer itself

## Validation

- `poetry run pytest`
- `poetry run ruff check .`

## Next Seam

- `run` from `simulate.py`
