# Module Spec 071: GOSM Model-Card And Traceability Foundation

## Purpose

Reopen the architecture for the root legacy `GOSM/` package by restoring the smallest migration seam that later numerical ports depend on: packaged model-card assets, equation-id access helpers, and traceability metadata utilities.

## Source Inputs

- `GOSM/model_card/C001.json` through `GOSM/model_card/C010.json`
- `GOSM/src/gosm/utils/traceability.py`
- `GOSM/src/gosm/__init__.py`

## Target Outputs

- `src/stomatal_optimiaztion/domains/gosm/`
- `src/stomatal_optimiaztion/domains/gosm/utils/`
- `tests/test_gosm_model_card.py`
- `tests/test_gosm_traceability.py`
- `tests/test_gosm_import_surface.py`

## Responsibilities

1. preserve packaged access to the root GOSM model-card JSON assets
2. preserve equation-id validation and decorator-based traceability metadata helpers
3. preserve a legacy-style `gosm.utils.traceability` import path for later numerical module ports

## Non-Goals

- migrate `GOSM/src/gosm/params/defaults.py`
- migrate numerical runtime modules under `GOSM/src/gosm/model/`
- open the root `TDGM` package in the same slice

## Validation

- `poetry run pytest`
- `poetry run ruff check .`

## Next Seam

- `TDGM/model_card/C001.json` through `TDGM/model_card/C006.json` plus `TDGM/src/tdgm/{implements.py,equation_registry.py,__init__.py}`
