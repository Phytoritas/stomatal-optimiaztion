## Summary
- migrate the `load-cell-data` preprocess-compare local server into `scripts/preprocess_compare_server.py`
- preserve export computation, preprocess job state handling, static serving, and repo-level CLI wiring
- move the next remaining `load-cell-data` seam to the static viewer builder

## Validation
- `.\\.venv\\Scripts\\python.exe -m pytest`
- `.\\.venv\\Scripts\\ruff.exe check .`

Closes #117
