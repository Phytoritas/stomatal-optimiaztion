## Summary
- migrate the `load-cell-data` synthetic validation harness seam into `domains/load_cell/synthetic_test.py`
- preserve deterministic synthetic dataset generation, truth totals, and end-to-end tolerance checks over the migrated pipeline
- mark the next remaining `load-cell-data` seam at the repo-level real-data benchmark harness

## Validation
- `.\\.venv\\Scripts\\python.exe -m pytest`
- `.\\.venv\\Scripts\\ruff.exe check .`

Closes #111
