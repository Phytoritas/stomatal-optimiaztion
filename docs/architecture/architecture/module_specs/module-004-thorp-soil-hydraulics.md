# Module Spec 004: THORP Soil Hydraulics

## Purpose

Migrate the THORP soil hydraulic dataclass as the first bounded hydraulic seam after the vulnerability primitive.

## Source Inputs

- `THORP/src/thorp/config.py` (`SoilHydraulics`)
- equation tags `E_S2_4` through `E_S2_8`

## Target Outputs

- `src/stomatal_optimiaztion/domains/thorp/soil_hydraulics.py`
- `tests/test_thorp_soil_hydraulics.py`

## Responsibilities

1. preserve the legacy van Genuchten-style soil hydraulic relationships
2. keep equation tags on the migrated methods for traceability
3. expose `k_soil` as the alias used by later soil-column logic

## Non-Goals

- port `THORPParams` from `config.py`
- port `initial_soil_and_roots` or the wider soil simulation logic
- merge soil hydraulics and vulnerability curves into one abstraction layer

## Validation

- `poetry run pytest`
- `poetry run ruff check .`

## Next Seam

- `richards_equation` from `soil.py`
