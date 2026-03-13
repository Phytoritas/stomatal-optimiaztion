## Why
- `slice 060` migrated the incremental preprocess harness, so the next remaining bounded `load-cell-data` surface is the preprocess-compare local server at `src/preprocess_compare_server.py`.
- The migrated repo now has canonical parquet updates and viewer JSON cache refresh, but it still lacks the HTTP server layer that exposes health, preprocess, cancel, and export APIs to the local compare viewer.
- This slice should stay server-bounded: export computation, preprocess job orchestration, local static serving, and repo-level CLI wiring only.

## Affected model
- `load-cell-data`
- `scripts/`
- preprocess-compare local server tests
- architecture docs for the next viewer/server seam

## Validation method
- `poetry run pytest`
- `poetry run ruff check .`
- add coverage for safe path checks, transpiration export computation, health/export/preprocess API responses, cancel flow, and CLI/default wiring

## Comparison target
- legacy `load-cell-data/src/preprocess_compare_server.py`
- current migrated `scripts/preprocess_incremental.py`
- deferred viewer-builder seam at `load-cell-data/src/build_preprocess_compare_viewer.py`
