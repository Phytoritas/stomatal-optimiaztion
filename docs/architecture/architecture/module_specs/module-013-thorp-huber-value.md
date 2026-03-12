# Module Spec 013: THORP Huber Value

## Purpose

Migrate the bounded `huber_value` seam so the new package can report THORP sapwood-to-leaf area ratios without importing the legacy simulation container.

## Source Inputs

- `THORP/src/thorp/metrics.py` (`huber_value`)
- `MODEL_CARD:C010` Huber-value reporting context

## Target Outputs

- `src/stomatal_optimiaztion/domains/thorp/metrics.py`
- `tests/test_thorp_metrics.py`

## Responsibilities

1. preserve the legacy sapwood-to-leaf area ratio calculation
2. expose minimal geometry-series and parameter dataclasses instead of porting `SimulationOutputs` and `THORPParams`
3. keep zero-leaf-area reporting behavior aligned with legacy `inf` and `NaN` outputs

## Non-Goals

- port `rooting_depth` from `metrics.py`
- port `soil_grid` reconstruction helpers
- port the full simulation output container

## Validation

- `poetry run pytest`
- `poetry run ruff check .`

## Next Seam

- `rooting_depth` from `metrics.py`
