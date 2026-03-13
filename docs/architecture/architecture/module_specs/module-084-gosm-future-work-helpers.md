# Module Spec 084: GOSM Future-Work Helpers

## Purpose

Restore the small root `GOSM/` helper surface that captures paper-alternative future-work formulas without widening into broader control or steady-state layers.

## Source Inputs

- `GOSM/src/gosm/model/future_work.py`
- `GOSM/src/gosm/model/__init__.py`

## Target Outputs

- `src/stomatal_optimiaztion/domains/gosm/model/`
- `tests/test_gosm_future_work.py`

## Responsibilities

1. preserve `Eq.S10.1` and `Eq.S10.2` tagging on the helper callables
2. preserve the growth-integral helper, legacy `Gamma` alias, and augmented-Lagrangian helper behavior
3. keep the seam isolated from the remaining stomatal-model and steady-state layers

## Non-Goals

- migrate `GOSM/src/gosm/model/stomata_models.py`
- migrate `GOSM/src/gosm/model/instantaneous.py`
- migrate `GOSM/src/gosm/model/steady_state.py`

## Validation

- `poetry run pytest`
- `poetry run ruff check .`

## Next Seam

- `GOSM/src/gosm/model/stomata_models.py`
