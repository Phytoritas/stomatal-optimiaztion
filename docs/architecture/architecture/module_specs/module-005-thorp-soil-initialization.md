# Module Spec 005: THORP Soil Initialization

## Purpose

Migrate the `initial_soil_and_roots` seam as the first bounded function that composes migrated hydraulic primitives into a full initialization output.

## Source Inputs

- `THORP/src/thorp/soil.py` (`SoilGrid`, `InitialSoilAndRoots`, `initial_soil_and_roots`)
- migrated dependencies: `SoilHydraulics`, `WeibullVC`

## Target Outputs

- `src/stomatal_optimiaztion/domains/thorp/soil_initialization.py`
- `tests/test_thorp_soil_initialization.py`

## Responsibilities

1. discretize the soil column consistently with legacy THORP behavior
2. initialize `psi_soil_by_layer`, `vwc`, `c_r_h`, and `c_r_v`
3. keep the function bounded by a minimal soil-initialization parameter dataclass rather than porting full `THORPParams`

## Non-Goals

- port `richards_equation` or `soil_moisture`
- port the full THORP configuration bundle
- absorb full soil time-stepping into this slice

## Validation

- `poetry run pytest`
- `poetry run ruff check .`

## Next Seam

- `soil_moisture` from `soil.py`
