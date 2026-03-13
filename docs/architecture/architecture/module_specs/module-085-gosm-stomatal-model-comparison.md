# Module Spec 085: GOSM Stomatal-Model Comparison

## Purpose

Restore the bounded root `GOSM/` analysis layer that compares alternative instantaneous stomatal optimization models over the migrated runtime sweep outputs.

## Source Inputs

- `GOSM/src/gosm/model/stomata_models.py`
- `GOSM/src/gosm/model/__init__.py`

## Target Outputs

- `src/stomatal_optimiaztion/domains/gosm/model/`
- `tests/test_gosm_stomata_models.py`

## Responsibilities

1. preserve the `Eq.S7.*`-tagged stomatal-model comparison helpers and their shared interpolation logic
2. preserve the legacy `HC_vec` alias plus no-crossing `NaN` contracts where the alternative models do not intersect the baseline marginal WUE curve
3. keep the seam isolated from `instantaneous.py`, `steady_state.py`, and example scripts

## Non-Goals

- migrate `GOSM/src/gosm/model/instantaneous.py`
- migrate `GOSM/src/gosm/model/steady_state.py`
- migrate root `GOSM` example scripts

## Validation

- `poetry run pytest`
- `poetry run ruff check .`

## Next Seam

- `GOSM/src/gosm/model/instantaneous.py`
