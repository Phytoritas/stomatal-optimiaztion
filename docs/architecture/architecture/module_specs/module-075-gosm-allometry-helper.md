# Module Spec 075: GOSM Allometry Helper

## Purpose

Open the next bounded root `GOSM/` runtime seam by restoring the leaf-area-index helper used by later steady-state, instantaneous, and pipeline kernels.

## Source Inputs

- `GOSM/src/gosm/model/allometry.py`
- `GOSM/src/gosm/model/__init__.py`

## Target Outputs

- `src/stomatal_optimiaztion/domains/gosm/model/`
- `tests/test_gosm_allometry.py`

## Responsibilities

1. preserve `Eq.S3.LAI` equation tagging on `leaf_area_index()`
2. preserve scalar and vector input support with NumPy coercion
3. keep the seam isolated from broader GOSM runtime orchestration

## Non-Goals

- migrate `GOSM/src/gosm/model/npp_gpp.py`
- migrate hydraulics, steady-state, or pipeline seams
- widen the root `gosm` package exports beyond the bounded kernel package path

## Validation

- `poetry run pytest`
- `poetry run ruff check .`

## Next Seam

- `GOSM/src/gosm/model/npp_gpp.py`
