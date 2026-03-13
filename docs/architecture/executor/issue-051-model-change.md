## Why
- `slice 050` opened the bounded `load-cell-data` preprocessing seam, so the next staged helper surface is the event-detection module at `loadcell_pipeline/events.py`.
- The migrated repo now has config, IO, aggregation, thresholds, and preprocessing helpers, but it still lacks the canonical derivative-to-label, event grouping, and event merge functions that downstream flux decomposition expects.
- This slice should stay events-bounded: point labeling, hysteresis labeling, event grouping, and close-event merge helpers only.

## Affected model
- `load-cell-data`
- `src/stomatal_optimiaztion/domains/load_cell/`
- related load-cell event tests and package exports

## Validation method
- `poetry run pytest`
- `poetry run ruff check .`
- add coverage for missing-column rejection, hysteresis validation, short-event filtering, close-event merging, and DataFrame-backed event mass recomputation

## Comparison target
- legacy `load-cell-data/loadcell_pipeline/events.py`
- current migrated `src/stomatal_optimiaztion/domains/load_cell/preprocessing.py`
