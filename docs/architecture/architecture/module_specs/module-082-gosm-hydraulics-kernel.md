# Module Spec 082: GOSM Hydraulics Kernel

## Purpose

Open the next bounded coupled root `GOSM/` runtime kernel by restoring the xylem hydraulics and turgor-limited potential growth solve.

## Source Inputs

- `GOSM/src/gosm/model/hydraulics.py`
- `GOSM/src/gosm/model/__init__.py`
- `GOSM/src/gosm/utils/math.py`

## Target Outputs

- `src/stomatal_optimiaztion/domains/gosm/model/`
- `tests/test_gosm_hydraulics.py`

## Responsibilities

1. preserve `Eq.S5.1` through `Eq.S6.15` equation tagging on the kernel
2. preserve hydraulic state outputs, turgor-growth outputs, and derivative propagation
3. keep the seam isolated from broader GOSM runtime orchestration

## Non-Goals

- migrate `GOSM/src/gosm/model/pipeline.py`
- migrate wider policy or control layers beyond the bounded kernel package path

## Validation

- `poetry run pytest`
- `poetry run ruff check .`

## Next Seam

- `GOSM/src/gosm/model/pipeline.py`
