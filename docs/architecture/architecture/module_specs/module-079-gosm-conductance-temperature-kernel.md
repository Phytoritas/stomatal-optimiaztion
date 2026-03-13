# Module Spec 079: GOSM Conductance Temperature Kernel

## Purpose

Open the first bounded coupled root `GOSM/` runtime kernel by restoring the leaf-temperature and conductance solve used by downstream assimilation and pipeline seams.

## Source Inputs

- `GOSM/src/gosm/model/conductance_temperature.py`
- `GOSM/src/gosm/model/__init__.py`

## Target Outputs

- `src/stomatal_optimiaztion/domains/gosm/model/`
- `tests/test_gosm_conductance_temperature.py`

## Responsibilities

1. preserve `Eq.S3.1` and `Eq.S3.3` through `Eq.S3.10` equation tagging on the kernel
2. preserve the coupled Newton solve, latent-heat calculation, conductance outputs, and derivative propagation
3. keep the seam isolated from broader GOSM runtime orchestration

## Non-Goals

- migrate `GOSM/src/gosm/model/carbon_assimilation.py`
- migrate hydraulics or pipeline seams
- widen the root `gosm` package exports beyond the bounded kernel package path

## Validation

- `poetry run pytest`
- `poetry run ruff check .`

## Next Seam

- `GOSM/src/gosm/model/carbon_assimilation.py`
