# Module Spec 077: GOSM Optimal Control Helpers

## Purpose

Open the next bounded root `GOSM/` objective-layer seam by restoring the optimal-control helper functions used by later steady-state and policy kernels.

## Source Inputs

- `GOSM/src/gosm/model/optimal_control.py`
- `GOSM/src/gosm/model/__init__.py`

## Target Outputs

- `src/stomatal_optimiaztion/domains/gosm/model/`
- `tests/test_gosm_optimal_control.py`

## Responsibilities

1. preserve `Eq.S2.1` through `Eq.S2.6` equation tagging on the helper functions
2. preserve scalar and vector behavior for objective, eta, chi, theta, and eta-dot calculations
3. keep the seam isolated from broader GOSM runtime orchestration

## Non-Goals

- migrate `GOSM/src/gosm/model/carbon_dynamics.py`
- migrate conductance-temperature, hydraulics, or pipeline seams
- widen the root `gosm` package exports beyond the bounded helper package path

## Validation

- `poetry run pytest`
- `poetry run ruff check .`

## Next Seam

- `GOSM/src/gosm/model/carbon_dynamics.py`
