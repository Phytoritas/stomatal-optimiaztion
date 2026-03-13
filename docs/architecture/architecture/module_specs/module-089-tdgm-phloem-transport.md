# Module Spec 089: TDGM Phloem Transport

## Purpose

Restore the bounded root `TDGM/` PTM kernel that downstream coupling and THORP-G postprocess seams depend on.

## Source Inputs

- `TDGM/src/tdgm/ptm.py`
- `TDGM/src/tdgm/__init__.py`

## Target Outputs

- `src/stomatal_optimiaztion/domains/tdgm/`
- `tests/test_tdgm_ptm.py`

## Responsibilities

1. preserve the `Eq_S1.*`-tagged PTM concentration helper and the sucrose-viscosity helper
2. preserve apex-concentration behavior and the physiological NaN guard branch
3. keep the seam isolated from coupling, equation-registry, and THORP-G postprocess tooling

## Non-Goals

- migrate `TDGM/src/tdgm/coupling.py`
- migrate `TDGM/src/tdgm/equation_registry.py`
- migrate `TDGM/src/tdgm/thorp_g_postprocess.py`

## Validation

- `poetry run pytest`
- `poetry run ruff check .`

## Next Seam

- `TDGM/src/tdgm/coupling.py`
