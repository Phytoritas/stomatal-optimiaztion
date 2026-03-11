# Module Spec 002: THORP Radiation Kernel

## Purpose

Migrate the first behavior-level THORP runtime seam into the new package without pulling in the broader simulation stack.

## Source Inputs

- `THORP/src/thorp/radiation.py`
- `THORP/tests/test_unit_behaviors.py`

## Target Outputs

- `src/stomatal_optimiaztion/domains/thorp/radiation.py`
- `tests/test_thorp_radiation.py`

## Responsibilities

1. preserve the THORP S.5 equation tags on the migrated callable
2. keep the numerical behavior aligned with the legacy snapshot
3. keep the implementation isolated from unrelated THORP config or simulation state

## Non-Goals

- port the full forcing or simulation pipeline
- introduce third-party dependencies just to support this seam
- widen the slice into canopy growth or allocation logic

## Validation

- `poetry run pytest`
- `poetry run ruff check .`

## Next Seam

- `SoilHydraulics` from `config.py`
