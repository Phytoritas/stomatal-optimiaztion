## Why
- `slice 056` opened the bounded `load-cell-data` end-to-end runner seam, so the next staged helper surface is the raw ALMEMO preprocessing module at `loadcell_pipeline/almemo_preprocess.py`.
- The migrated repo now has a lazy preprocessing hook in `run_all`, but it still lacks the concrete raw CSV reader, channel standardizer, duplicate-timestamp merge, and optional 1-second interpolation seam.
- This slice should stay preprocessing-bounded: raw ALMEMO ingestion, canonical column mapping, precision-preserving CSV writing, and CLI wiring only.

## Affected model
- `load-cell-data`
- `src/stomatal_optimiaztion/domains/load_cell/`
- related load-cell preprocessing tests and package exports

## Validation method
- `poetry run pytest`
- `poetry run ruff check .`
- add coverage for raw header parsing, canonical channel mapping, duplicate-timestamp merge, interpolation behavior, folder preprocessing, and CLI output

## Comparison target
- legacy `load-cell-data/loadcell_pipeline/almemo_preprocess.py`
- current migrated `src/stomatal_optimiaztion/domains/load_cell/run_all.py`
