# Module Spec 010: THORP Allocation Fractions

## Purpose

Migrate the bounded `allocation_fractions` seam so the new package can convert migrated stomatal outputs into plant carbon allocation fractions.

## Source Inputs

- `THORP/src/thorp/allocation.py` (`allocation_fractions`)
- migrated dependencies: stomatal derivative outputs

## Target Outputs

- `src/stomatal_optimiaztion/domains/thorp/allocation.py`
- `tests/test_thorp_allocation.py`

## Responsibilities

1. preserve bounded carbon-allocation scoring and normalization logic
2. keep equation tags for `E_S8_1` through `E_S8_12`
3. expose a minimal parameter dataclass instead of porting full `THORPParams`

## Non-Goals

- port `grow` from `growth.py`
- port whole-plant carbon state integration
- merge allocation and growth into one abstraction

## Validation

- `poetry run pytest`
- `poetry run ruff check .`

## Next Seam

- `biomass_fractions` from `metrics.py`
