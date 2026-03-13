## Why
- `slice 061` migrated the preprocess-compare local server, so the next remaining bounded `load-cell-data` surface is the static viewer builder at `src/build_preprocess_compare_viewer.py`.
- The migrated repo now has the HTTP server and viewer data refresh path, but it still lacks the repo-level builder that materializes `index.html`, bundled assets, and day JSON payloads for the compare UI.
- This slice should stay viewer-builder-bounded: canonical day discovery, transpiration fallback loading, static asset writing, day JSON export, and repo-level CLI wiring only.

## Affected model
- `load-cell-data`
- `scripts/`
- preprocess-compare viewer build tests
- architecture docs for the final viewer seam

## Validation method
- `poetry run pytest`
- `poetry run ruff check .`
- add coverage for canonical day selection, transpiration fallback computation, static asset output, viewer data JSON generation, and CLI/default wiring

## Comparison target
- legacy `load-cell-data/src/build_preprocess_compare_viewer.py`
- current migrated `scripts/preprocess_compare_server.py`
- current migrated `scripts/preprocess_incremental.py`
