# Module Spec 009: THORP Stomata

## Purpose

Migrate the bounded `stomata` seam so the new package can close coupled hydraulics and gas exchange on migrated THORP primitives.

## Source Inputs

- `THORP/src/thorp/hydraulics.py` (`stomata`)
- migrated dependencies: `e_from_soil_to_root_collar`, `WeibullVC`

## Target Outputs

- `src/stomatal_optimiaztion/domains/thorp/hydraulics.py`
- `tests/test_thorp_stomata.py`

## Responsibilities

1. preserve the bounded stomatal-closure search and photosynthesis coupling logic
2. keep equation tags for `E_S3_6` through `E_S6_16`
3. expose a minimal parameter dataclass instead of porting full `THORPParams`

## Non-Goals

- port `allocation_fractions` from `allocation.py`
- port whole-plant growth or simulation orchestration
- merge all remaining THORP runtime into one abstraction

## Validation

- `poetry run pytest`
- `poetry run ruff check .`

## Next Seam

- `grow` from `growth.py`
