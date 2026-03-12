# Module Spec 014: THORP Rooting Depth

## Purpose

Migrate the bounded `rooting_depth` seam so the new package can report THORP root-distribution depth percentiles without importing the legacy simulation container.

## Source Inputs

- `THORP/src/thorp/metrics.py` (`rooting_depth`)
- migrated `SoilGrid` from `soil_initialization.py`

## Target Outputs

- `src/stomatal_optimiaztion/domains/thorp/metrics.py`
- `tests/test_thorp_metrics.py`

## Responsibilities

1. preserve the legacy percentile-based rooting-depth calculation
2. expose a minimal root time-series dataclass instead of porting `SimulationOutputs`
3. reuse migrated `SoilGrid` rather than reconstructing the legacy `THORPParams` bundle

## Non-Goals

- port `soil_grid` from `metrics.py`
- port the full simulation output container
- port broader soil reporting utilities beyond `rooting_depth`

## Validation

- `poetry run pytest`
- `poetry run ruff check .`

## Next Seam

- `soil_grid` from `metrics.py`
