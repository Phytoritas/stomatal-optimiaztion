## Why
- `slice 047` opened the bounded `load-cell-data` IO seam, so the next staged helper surface is the time-aggregation module at `loadcell_pipeline/aggregation.py`.
- The migrated repo can now read and write per-second data, but it still lacks the canonical resampling and daily-summary helpers used by later workflow and CLI paths.
- This slice should stay aggregation-bounded: time-step resampling, daily summary assembly, and metadata passthrough only.

## Affected model
- `load-cell-data`
- `src/stomatal_optimiaztion/domains/load_cell/`
- related load-cell aggregation tests and package exports

## Validation method
- `poetry run pytest`
- `poetry run ruff check .`
- add coverage for required-column validation, resampled flux totals/rates, daily summary event counts, label-derived durations, and metadata passthrough

## Comparison target
- legacy `load-cell-data/loadcell_pipeline/aggregation.py`
- current migrated `src/stomatal_optimiaztion/domains/load_cell/io.py`
