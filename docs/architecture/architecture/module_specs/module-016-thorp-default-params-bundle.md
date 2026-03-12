# Module Spec 016: THORP Default Params Bundle

## Purpose

Migrate the bounded `default_params` seam so the new package can expose canonical legacy-like defaults for already migrated THORP seams without porting the full legacy `THORPParams` dataclass.

## Source Inputs

- `THORP/src/thorp/config.py` (`default_params`)
- migrated parameter dataclasses across `soil_initialization`, `soil_dynamics`, `hydraulics`, `allocation`, `growth`, and `metrics`

## Target Outputs

- `src/stomatal_optimiaztion/domains/thorp/defaults.py`
- `tests/test_thorp_defaults.py`

## Responsibilities

1. preserve legacy default constants and closure outputs for already migrated seams
2. expose one bounded defaults bundle instead of reintroducing the full `THORPParams` structure
3. allow migrated tests and adapters to reuse a single canonical source of default parameter values

## Non-Goals

- port the legacy `THORPParams` dataclass
- port forcing-path setup or file-system dependent configuration
- port simulation orchestration or remaining config-only seams

## Validation

- `poetry run pytest`
- `poetry run ruff check .`

## Next Seam

- `THORPParams` from `config.py`
