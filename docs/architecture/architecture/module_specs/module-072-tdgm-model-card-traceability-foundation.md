# Module Spec 072: TDGM Model-Card And Traceability Foundation

## Purpose

Open the parallel root `TDGM/` architecture wave by restoring the smallest migration seam that later runtime ports depend on: packaged model-card assets, equation-id access helpers, and traceability metadata utilities.

## Source Inputs

- `TDGM/model_card/C001.json` through `TDGM/model_card/C006.json`
- `TDGM/src/tdgm/implements.py`
- `TDGM/src/tdgm/__init__.py`

## Target Outputs

- `src/stomatal_optimiaztion/domains/tdgm/`
- `tests/test_tdgm_model_card.py`
- `tests/test_tdgm_traceability.py`
- `tests/test_tdgm_import_surface.py`

## Responsibilities

1. preserve packaged access to the root TDGM model-card JSON assets
2. preserve equation-id validation and decorator-based traceability metadata helpers
3. preserve a root `domains.tdgm` import surface that later PTM, TDGM, and THORP-G runtime seams can land on without rename churn

## Non-Goals

- migrate `TDGM/src/tdgm/ptm.py`
- migrate `TDGM/src/tdgm/turgor_growth.py`
- migrate `TDGM/src/tdgm/coupling.py` or THORP-G runtime adapters
- widen into root `GOSM` numerical seams in the same slice

## Validation

- `poetry run pytest`
- `poetry run ruff check .`

## Next Seam

- `GOSM/src/gosm/params/defaults.py`
