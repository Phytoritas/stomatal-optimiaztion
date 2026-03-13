## Why
- `slice 048` opened the bounded `load-cell-data` aggregation seam, so the next staged helper surface is the adaptive threshold detector at `loadcell_pipeline/thresholds.py`.
- The migrated repo now has config, IO, and aggregation helpers, but it still lacks the canonical threshold estimator that later event-labeling and workflow seams depend on.
- This slice should stay threshold-bounded: derivative distribution filtering, robust sigma estimation, and irrigation/drainage threshold output only.

## Affected model
- `load-cell-data`
- `src/stomatal_optimiaztion/domains/load_cell/`
- related load-cell threshold tests and package exports

## Validation method
- `poetry run pytest`
- `poetry run ruff check .`
- add coverage for empty-series rejection, valid-mask fallback behavior, minimum sigma fallback, physical sign constraints, and logger diagnostics

## Comparison target
- legacy `load-cell-data/loadcell_pipeline/thresholds.py`
- current migrated `src/stomatal_optimiaztion/domains/load_cell/aggregation.py`
