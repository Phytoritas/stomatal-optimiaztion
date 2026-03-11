# Module Spec 006: THORP Richards Equation

## Purpose

Migrate the bounded Richards-equation solver so the soil column dynamics can run on migrated primitives without pulling in the full surface-flux layer.

## Source Inputs

- `THORP/src/thorp/soil.py` (`richards_equation`)
- migrated dependencies: `SoilGrid`, `SoilHydraulics`

## Target Outputs

- `src/stomatal_optimiaztion/domains/thorp/soil_dynamics.py`
- `tests/test_thorp_richards_equation.py`

## Responsibilities

1. preserve the THORP Richards-equation matrix solve and boundary-condition handling
2. keep equation tags for `E_S2_1`, `E_S2_10`, and `E_S2_13` through `E_S2_26`
3. expose a minimal parameter dataclass instead of porting full `THORPParams`

## Non-Goals

- port `soil_moisture`
- port surface energy or evaporation coupling
- merge the full soil module into one large translation unit

## Validation

- `poetry run pytest`
- `poetry run ruff check .`

## Next Seam

- `soil_moisture` from `soil.py`
