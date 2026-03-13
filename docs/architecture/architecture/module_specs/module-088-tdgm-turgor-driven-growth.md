# Module Spec 088: TDGM Turgor-Driven Growth

## Purpose

Open the first numerical root `TDGM/` runtime seam by restoring the bounded turgor-driven growth kernel on top of the migrated package foundation.

## Source Inputs

- `TDGM/src/tdgm/turgor_growth.py`
- `TDGM/src/tdgm/__init__.py`

## Target Outputs

- `src/stomatal_optimiaztion/domains/tdgm/`
- `tests/test_tdgm_turgor_growth.py`

## Responsibilities

1. preserve `Eq_S2.12` and `Eq_S2.16` tagging on the growth kernel
2. preserve scalar and vector whole-tree growth-rate behavior over the baseline osmotic and turgor formulas
3. keep the seam isolated from PTM, coupling, and THORP-G postprocess layers

## Non-Goals

- migrate `TDGM/src/tdgm/ptm.py`
- migrate `TDGM/src/tdgm/coupling.py`
- migrate `TDGM/src/tdgm/thorp_g_postprocess.py`

## Validation

- `poetry run pytest`
- `poetry run ruff check .`

## Next Seam

- `TDGM/src/tdgm/ptm.py`
