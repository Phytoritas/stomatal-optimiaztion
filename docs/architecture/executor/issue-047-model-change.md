## Why
- `slice 046` opened the first `load-cell-data` package boundary, so the next bounded seam is the ingestion and result-writing helper surface at `loadcell_pipeline/io.py`.
- The migrated repo now has config helpers but still lacks the canonical CSV reader and artifact writer functions that later preprocessing and workflow seams depend on.
- This slice should stay IO-bounded: CSV ingestion, interpolation flags, and result writers only.

## Affected model
- `load-cell-data`
- `src/stomatal_optimiaztion/domains/load_cell/`
- related load-cell IO tests and package exports

## Validation method
- `poetry run pytest`
- `poetry run ruff check .`
- add coverage for CSV ingestion, duplicate timestamp handling, interpolation flags, multi-resolution output writing, and error paths

## Comparison target
- legacy `load-cell-data/loadcell_pipeline/io.py`
- current migrated `src/stomatal_optimiaztion/domains/load_cell/config.py`
