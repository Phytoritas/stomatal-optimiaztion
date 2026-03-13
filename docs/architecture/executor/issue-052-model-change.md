## Why
- `slice 051` opened the bounded `load-cell-data` events seam, so the next staged helper surface is the flux-decomposition module at `loadcell_pipeline/fluxes.py`.
- The migrated repo now has config, IO, aggregation, thresholds, preprocessing, and events helpers, but it still lacks the canonical irrigation/drainage/transpiration split and water-balance reconstruction that the pipeline surface depends on.
- This slice should stay flux-bounded: per-second flux decomposition, event-gap transpiration interpolation, cumulative sums, and water-balance scaling only.

## Affected model
- `load-cell-data`
- `src/stomatal_optimiaztion/domains/load_cell/`
- related load-cell flux tests and package exports

## Validation method
- `poetry run pytest`
- `poetry run ruff check .`
- add coverage for required-column rejection, baseline/event flux splitting, optional transpiration interpolation, and min/max water-balance scale guardrails

## Comparison target
- legacy `load-cell-data/loadcell_pipeline/fluxes.py`
- current migrated `src/stomatal_optimiaztion/domains/load_cell/events.py`
