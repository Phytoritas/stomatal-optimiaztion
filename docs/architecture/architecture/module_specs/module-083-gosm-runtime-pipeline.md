# Module Spec 083: GOSM Runtime Pipeline

## Purpose

Close the first fully wired root `GOSM/` runtime path by restoring the bounded orchestration layer that stitches together the already migrated radiation, hydraulics, conductance-temperature, and carbon-assimilation kernels.

## Source Inputs

- `GOSM/src/gosm/model/pipeline.py`
- `GOSM/src/gosm/model/__init__.py`

## Target Outputs

- `src/stomatal_optimiaztion/domains/gosm/model/`
- `tests/test_gosm_pipeline.py`

## Responsibilities

1. preserve the stage-level `S3` through `S6` tagging on the runtime pipeline seam
2. preserve the canonical kernel ordering and output tuple shape used by downstream root `GOSM` helpers
3. keep the seam isolated from the remaining helper and steady-state layers

## Non-Goals

- migrate `GOSM/src/gosm/model/future_work.py`
- migrate `GOSM/src/gosm/model/instantaneous.py`
- widen the root `gosm` package exports beyond the bounded model package surface

## Validation

- `poetry run pytest`
- `poetry run ruff check .`

## Next Seam

- `GOSM/src/gosm/model/future_work.py`
