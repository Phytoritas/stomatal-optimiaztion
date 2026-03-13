# Module Spec 078: GOSM Carbon Dynamics Helpers

## Purpose

Open the next bounded root `GOSM/` carbon-balance seam by restoring the NSC limitation, respiration, growth, and NSC-rate helper functions used by later runtime kernels.

## Source Inputs

- `GOSM/src/gosm/model/carbon_dynamics.py`
- `GOSM/src/gosm/model/__init__.py`

## Target Outputs

- `src/stomatal_optimiaztion/domains/gosm/model/`
- `tests/test_gosm_carbon_dynamics.py`

## Responsibilities

1. preserve `Eq.S1.1` through `Eq.S1.9` equation tagging across the helper functions
2. preserve scalar and vector behavior for NSC limitation, respiration, growth, and NSC-rate calculations
3. keep the seam isolated from broader GOSM runtime orchestration

## Non-Goals

- migrate `GOSM/src/gosm/model/conductance_temperature.py`
- migrate hydraulics, carbon-assimilation, or pipeline seams
- widen the root `gosm` package exports beyond the bounded helper package path

## Validation

- `poetry run pytest`
- `poetry run ruff check .`

## Next Seam

- `GOSM/src/gosm/model/conductance_temperature.py`
