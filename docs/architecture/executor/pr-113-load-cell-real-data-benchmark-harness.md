## Summary
- migrate the `load-cell-data` real-data benchmark harness into `scripts/real_data_benchmark.py`
- preserve batch summary/comparison/failure outputs over the migrated `load_cell` pipeline
- move the next remaining `load-cell-data` seam to the preprocess-compare incremental tooling

## Validation
- `.\\.venv\\Scripts\\python.exe -m pytest`
- `.\\.venv\\Scripts\\ruff.exe check .`

Closes #113
