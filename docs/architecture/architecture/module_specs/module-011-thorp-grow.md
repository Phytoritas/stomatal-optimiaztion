# Module Spec 011: THORP Grow

## Purpose

Migrate the bounded `grow` seam so the new package can update THORP structural carbon pools and derived geometry from migrated allocation outputs.

## Source Inputs

- `THORP/src/thorp/growth.py` (`GrowthState`, `grow`)
- migrated dependencies: `AllocationFractions`

## Target Outputs

- `src/stomatal_optimiaztion/domains/thorp/growth.py`
- `tests/test_thorp_growth.py`

## Responsibilities

1. preserve bounded growth-state updates, senescence handling, and geometry reconstruction
2. keep equation tags for `E_S7_1` through `E_S9_9`
3. expose a minimal parameter dataclass instead of porting full `THORPParams`

## Non-Goals

- port `biomass_fractions` or other reporting helpers from `metrics.py`
- port the full simulation loop
- merge growth, allocation, and metrics into one abstraction

## Validation

- `poetry run pytest`
- `poetry run ruff check .`

## Next Seam

- `biomass_fractions` from `metrics.py`
