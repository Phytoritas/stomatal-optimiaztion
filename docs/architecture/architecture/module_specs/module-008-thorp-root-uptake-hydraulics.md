# Module Spec 008: THORP Root Uptake Hydraulics

## Purpose

Migrate the bounded `e_from_soil_to_root_collar` seam so the new package can compute root uptake from migrated soil, root, and vulnerability primitives.

## Source Inputs

- `THORP/src/thorp/hydraulics.py` (`e_from_soil_to_root_collar`)
- migrated dependencies: `WeibullVC`, `SoilGrid`, `InitialSoilAndRoots`

## Target Outputs

- `src/stomatal_optimiaztion/domains/thorp/hydraulics.py`
- `tests/test_thorp_root_uptake.py`

## Responsibilities

1. preserve the bounded soil-to-root-collar uptake calculation and resistance bookkeeping
2. keep equation tags for `E_S2_2` and `E_S3_1` through `E_S3_5`
3. expose a minimal parameter dataclass instead of porting full `THORPParams`

## Non-Goals

- port `stomata` from `hydraulics.py`
- port canopy conductance or photosynthesis coupling
- merge all THORP hydraulics into one large translation unit

## Validation

- `poetry run pytest`
- `poetry run ruff check .`

## Next Seam

- `stomata` from `hydraulics.py`
