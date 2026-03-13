## Summary
- migrate the `load-cell-data` incremental preprocess harness into `scripts/preprocess_incremental.py`
- preserve marker tracking, canonical/transpiration parquet outputs, optional viewer cache refresh, and repo-level CLI defaults
- move the next remaining `load-cell-data` seam to the preprocess-compare local server

## Validation
- `.\\.venv\\Scripts\\python.exe -m pytest`
- `.\\.venv\\Scripts\\ruff.exe check .`

Closes #115
