# Module Spec 012: THORP Biomass Fractions

## Purpose

Migrate the bounded `biomass_fractions` seam so the new package can convert THORP carbon-pool time series into reported biomass fractions without importing the legacy simulation container.

## Source Inputs

- `THORP/src/thorp/metrics.py` (`BiomassFractions`, `biomass_fractions`)
- `MODEL_CARD:C010` biomass-conversion assumptions

## Target Outputs

- `src/stomatal_optimiaztion/domains/thorp/metrics.py`
- `tests/test_thorp_metrics.py`

## Responsibilities

1. preserve the legacy LMF, SMF, and RMF conversions from carbon pools
2. expose a minimal time-series dataclass instead of porting `SimulationOutputs`
3. keep zero-total reporting behavior aligned with legacy `NaN` outputs

## Non-Goals

- port `huber_value` from `metrics.py`
- port soil-grid reconstruction helpers or rooting-depth metrics
- port the full simulation output container

## Validation

- `poetry run pytest`
- `poetry run ruff check .`

## Next Seam

- `huber_value` from `metrics.py`
