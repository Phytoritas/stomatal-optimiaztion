# Module Spec 019: THORP Simulation Outputs

## Purpose

Migrate the bounded `SimulationOutputs` seam so the new package can expose one canonical THORP result surface before porting storage and time-stepping orchestration.

## Source Inputs

- `THORP/src/thorp/simulate.py` (`SimulationOutputs`)

## Target Outputs

- `src/stomatal_optimiaztion/domains/thorp/simulation.py`
- `tests/test_thorp_simulation_outputs.py`

## Responsibilities

1. preserve the legacy result field surface used by reporting and export adapters
2. preserve the `as_mat_dict()` mapping to legacy MAT output keys
3. keep the seam storage-only so the next simulation slice can port buffering logic independently

## Non-Goals

- port `_Store` from `simulate.py`
- port `simulate` or MAT-file export
- change result naming or output-key compatibility

## Validation

- `poetry run pytest`
- `poetry run ruff check .`

## Next Seam

- `_initial_allometry` from `simulate.py`
