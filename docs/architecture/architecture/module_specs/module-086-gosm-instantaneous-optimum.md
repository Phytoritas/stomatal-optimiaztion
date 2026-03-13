# Module Spec 086: GOSM Instantaneous Optimum

## Purpose

Restore the bounded root `GOSM/` helper that solves the fixed-eta, fixed-NSC instantaneous operating point over the migrated runtime sweep outputs.

## Source Inputs

- `GOSM/src/gosm/model/instantaneous.py`
- `GOSM/src/gosm/model/__init__.py`

## Target Outputs

- `src/stomatal_optimiaztion/domains/gosm/model/`
- `tests/test_gosm_instantaneous.py`

## Responsibilities

1. preserve `Eq.S2.4a` and `Eq.S2.4b` tagging on the instantaneous optimum helper
2. preserve the zero-crossing interpolation branch, all-negative-conductance branch, and lambda-zero bisection fallback
3. keep the seam isolated from `steady_state.py` and example scripts

## Non-Goals

- migrate `GOSM/src/gosm/model/steady_state.py`
- migrate root `GOSM` example scripts
- redesign the runtime pipeline output contract

## Validation

- `poetry run pytest`
- `poetry run ruff check .`

## Next Seam

- `GOSM/src/gosm/model/steady_state.py`
