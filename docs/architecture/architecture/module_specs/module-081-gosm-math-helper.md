# Module Spec 081: GOSM Math Helper

## Purpose

Open the small root `GOSM/` utility seam required by the hydraulics kernel by restoring the `polylog2()` helper.

## Source Inputs

- `GOSM/src/gosm/utils/math.py`
- `GOSM/src/gosm/utils/__init__.py`

## Target Outputs

- `src/stomatal_optimiaztion/domains/gosm/utils/`
- `tests/test_gosm_math.py`

## Responsibilities

1. preserve the `polylog2()` compatibility surface used by later hydraulics formulas
2. preserve scalar and vector behavior
3. keep the seam isolated from broader GOSM runtime orchestration

## Non-Goals

- migrate `GOSM/src/gosm/model/hydraulics.py`
- widen the root `gosm` package exports beyond the bounded utils package path

## Validation

- `poetry run pytest`
- `poetry run ruff check .`

## Next Seam

- `GOSM/src/gosm/model/hydraulics.py`
