# Module Spec 076: GOSM NPP GPP Helper

## Purpose

Open the next bounded root `GOSM/` metabolic seam by restoring the NPP/GPP helper functions used for parameter estimation and steady-state reporting.

## Source Inputs

- `GOSM/src/gosm/model/npp_gpp.py`
- `GOSM/src/gosm/model/__init__.py`

## Target Outputs

- `src/stomatal_optimiaztion/domains/gosm/model/`
- `tests/test_gosm_npp_gpp.py`

## Responsibilities

1. preserve `Eq.S8.1` and `Eq.S8.2` equation tagging on the helper functions
2. preserve scalar and vector behavior for the steady-state ratio calculation
3. keep the seam isolated from broader GOSM runtime orchestration

## Non-Goals

- migrate `GOSM/src/gosm/model/optimal_control.py`
- migrate carbon-dynamics, hydraulics, or pipeline seams
- widen the root `gosm` package exports beyond the bounded helper package path

## Validation

- `poetry run pytest`
- `poetry run ruff check .`

## Next Seam

- `GOSM/src/gosm/model/optimal_control.py`
