## Summary
- migrate the `load-cell-data` raw ALMEMO preprocessing seam into `domains/load_cell/almemo_preprocess.py`
- preserve raw CSV parsing, canonical channel mapping, duplicate merge, optional 1-second interpolation, and package-local CLI wiring
- reconnect the migrated `run_all` seam to the concrete preprocessing implementation and keep the next remaining seam at `synthetic_test.py`

## Validation
- `.\\.venv\\Scripts\\python.exe -m pytest`
- `.\\.venv\\Scripts\\ruff.exe check .`

Closes #109
