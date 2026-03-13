# Module Spec 087: GOSM Steady-State Helper

## Purpose

Restore the bounded root `GOSM/` helper that solves the steady-state NSC, CUE, and operating-point quantities used by the legacy control and sensitivity analyses.

## Source Inputs

- `GOSM/src/gosm/model/steady_state.py`
- `GOSM/src/gosm/model/__init__.py`

## Target Outputs

- `src/stomatal_optimiaztion/domains/gosm/model/`
- `tests/test_gosm_steady_state.py`

## Responsibilities

1. preserve `Eq.S1.9` and `Eq.S2.4b` tagging on the steady-state helper
2. preserve the vectorized Newton branch, quadratic NSC shortcut, and no-crossing/no-anchor contracts
3. keep the seam isolated from root `GOSM` example scripts and the upcoming root `TDGM` runtime wave

## Non-Goals

- migrate root `GOSM` example scripts
- redesign the runtime pipeline or instantaneous helper contracts
- open root `TDGM` runtime seams in the same slice

## Validation

- `poetry run pytest`
- `poetry run ruff check .`

## Next Seam

- `TDGM/src/tdgm/turgor_growth.py`
