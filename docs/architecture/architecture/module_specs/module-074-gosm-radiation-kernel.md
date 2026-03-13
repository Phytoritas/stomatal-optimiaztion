# Module Spec 074: GOSM Radiation Kernel

## Purpose

Open the first bounded root `GOSM/` runtime kernel by restoring the leaf-area-specific absorbed-radiation calculation used by later hydraulics and pipeline seams.

## Source Inputs

- `GOSM/src/gosm/model/radiation.py`
- `GOSM/src/gosm/model/__init__.py`

## Target Outputs

- `src/stomatal_optimiaztion/domains/gosm/model/`
- `tests/test_gosm_radiation.py`

## Responsibilities

1. preserve `Eq.S3.2` equation tagging on `radiation_absorbed()`
2. preserve zenith-angle clamping and the legacy negative-radiation guardrail
3. keep the seam isolated from broader GOSM runtime orchestration

## Non-Goals

- migrate `GOSM/src/gosm/model/allometry.py`
- migrate hydraulics, conductance-temperature, or pipeline seams
- widen the root `gosm` package exports beyond the bounded kernel package path

## Validation

- `poetry run pytest`
- `poetry run ruff check .`

## Next Seam

- `GOSM/src/gosm/model/allometry.py`
