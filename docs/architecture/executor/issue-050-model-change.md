## Why
- `slice 049` opened the bounded `load-cell-data` threshold-detection seam, so the next staged helper surface is the signal preprocessing module at `loadcell_pipeline/preprocessing.py`.
- The migrated repo now has config, IO, aggregation, and threshold helpers, but it still lacks the canonical outlier-correction and smoothing functions that upstream event detection depends on.
- This slice should stay preprocessing-bounded: outlier detection/correction, smoothing, and derivative reconstruction only.

## Affected model
- `load-cell-data`
- `src/stomatal_optimiaztion/domains/load_cell/`
- related load-cell preprocessing tests and package exports

## Validation method
- `poetry run pytest`
- `poetry run ruff check .`
- add coverage for missing-column rejection, short-series handling, invalid parameter rejection, Savitzky-Golay fallback/error paths, and derivative modes

## Comparison target
- legacy `load-cell-data/loadcell_pipeline/preprocessing.py`
- current migrated `src/stomatal_optimiaztion/domains/load_cell/thresholds.py`
