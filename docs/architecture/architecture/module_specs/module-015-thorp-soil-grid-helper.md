# Module Spec 015: THORP Soil Grid Helper

## Purpose

Migrate the bounded `soil_grid` helper seam so the new package can reconstruct the THORP soil grid without importing the legacy `THORPParams` bundle.

## Source Inputs

- `THORP/src/thorp/metrics.py` (`soil_grid`)
- migrated `SoilInitializationParams` and `initial_soil_and_roots`

## Target Outputs

- `src/stomatal_optimiaztion/domains/thorp/metrics.py`
- `tests/test_thorp_metrics.py`

## Responsibilities

1. preserve the legacy helper behavior of reconstructing the soil grid via initialization logic
2. reuse migrated `SoilInitializationParams` as the helper boundary
3. keep the wrapper narrow instead of reintroducing the legacy `THORPParams` bundle

## Non-Goals

- port `default_params` from `config.py`
- port the legacy `THORPParams` dataclass
- port simulation orchestration or forcing setup

## Validation

- `poetry run pytest`
- `poetry run ruff check .`

## Next Seam

- `THORPParams` from `config.py`
