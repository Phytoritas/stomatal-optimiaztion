# Module Spec 007: THORP Soil Moisture

## Purpose

Migrate the bounded `soil_moisture` seam so the soil column can couple surface evaporation and precipitation to the migrated Richards-equation solver.

## Source Inputs

- `THORP/src/thorp/soil.py` (`soil_moisture`)
- migrated dependencies: `SoilGrid`, `SoilHydraulics`, `richards_equation`

## Target Outputs

- `src/stomatal_optimiaztion/domains/thorp/soil_dynamics.py`
- `tests/test_thorp_soil_moisture.py`

## Responsibilities

1. preserve the legacy top-boundary source term and evaporation clamp behavior
2. keep equation tags for `E_S2_3`, `E_S2_9`, `E_S2_11`, and `E_S2_12`
3. expose a minimal parameter dataclass instead of porting full `THORPParams`

## Non-Goals

- port `e_from_soil_to_root_collar` from `hydraulics.py`
- port stomatal optimization or forcing orchestration
- merge the full soil and hydraulics runtime into one abstraction

## Validation

- `poetry run pytest`
- `poetry run ruff check .`

## Next Seam

- `stomata` from `hydraulics.py`
