# Module Spec 091: TDGM Equation Registry

## Purpose

Restore the bounded root `TDGM/` equation-registry module that assembles traceability coverage across the migrated PTM, turgor-growth, and coupling seams.

## Source Inputs

- `TDGM/src/tdgm/equation_registry.py`
- migrated `ptm.py`, `turgor_growth.py`, and `coupling.py`

## Target Outputs

- `src/stomatal_optimiaztion/domains/tdgm/equation_registry.py`
- `tests/test_tdgm_equation_registry.py`

## Responsibilities

1. preserve the no-argument registry surface that discovers annotated callables from migrated TDGM runtime modules
2. preserve equation-to-callable grouping over PTM, turgor-growth, and coupling helpers
3. keep the seam isolated from THORP-G postprocess IO and root package import-surface churn

## Non-Goals

- migrate `TDGM/src/tdgm/thorp_g_postprocess.py`
- replace the generic `traceability.py` helpers
- widen the seam into MATLAB-control-data validation

## Validation

- `poetry run pytest`
- `poetry run ruff check .`

## Next Seam

- `TDGM/src/tdgm/thorp_g_postprocess.py`
