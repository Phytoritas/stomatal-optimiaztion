## Why
- `slice 059` migrated the real-data benchmark harness seam, so the next remaining bounded `load-cell-data` surface is the preprocess-compare incremental tooling at `src/preprocess_incremental.py`.
- The migrated repo now has raw preprocessing, batch workflow, synthetic validation, and real-data benchmarking, but it still lacks the incremental parquet-plus-viewer-cache updater that the local compare tooling depends on.
- This slice should stay incremental-tooling-bounded: marker tracking, canonical parquet upsert, transpiration parquet emission, optional viewer JSON cache refresh, and repo-level CLI wiring only.

## Affected model
- `load-cell-data`
- `scripts/`
- runtime dependency surface for parquet IO
- related incremental-tooling tests and architecture docs

## Validation method
- `poetry run pytest`
- `poetry run ruff check .`
- add coverage for marker loading, canonical/transpiration parquet writes, viewer cache refresh, incremental skip logic, cancellation handling, and CLI/default config wiring

## Comparison target
- legacy `load-cell-data/src/preprocess_incremental.py`
- current migrated `src/stomatal_optimiaztion/domains/load_cell/almemo_preprocess.py`
