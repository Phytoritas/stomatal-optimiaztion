# Module Spec 080: GOSM Carbon Assimilation Kernel

## Purpose

Open the next bounded coupled root `GOSM/` biochemical runtime kernel by restoring the carbon-assimilation solve and marginal-WUE calculation used by downstream control and pipeline seams.

## Source Inputs

- `GOSM/src/gosm/model/carbon_assimilation.py`
- `GOSM/src/gosm/model/__init__.py`

## Target Outputs

- `src/stomatal_optimiaztion/domains/gosm/model/`
- `tests/test_gosm_carbon_assimilation.py`

## Responsibilities

1. preserve `Eq.S4.1` through `Eq.S4.18` equation tagging on the kernel
2. preserve the bounded assimilation solve, respiratory terms, and marginal-WUE calculation
3. keep the seam isolated from broader GOSM runtime orchestration

## Non-Goals

- migrate `GOSM/src/gosm/model/hydraulics.py`
- migrate the full pipeline seam
- widen the root `gosm` package exports beyond the bounded kernel package path

## Validation

- `poetry run pytest`
- `poetry run ruff check .`

## Next Seam

- `GOSM/src/gosm/model/hydraulics.py`
