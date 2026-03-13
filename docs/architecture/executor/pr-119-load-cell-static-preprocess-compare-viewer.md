## Summary
- migrate the legacy `load-cell-data` static preprocess-compare viewer builder into `scripts/build_preprocess_compare_viewer.py`
- preserve day selection, transpiration fallback loading, static asset writing, and repo-level CLI wiring
- close the remaining `load-cell-data/src` seam and move the next action to a post-domain workspace re-audit

## Validation
- `.\\.venv\\Scripts\\python.exe -m pytest`
- `.\\.venv\\Scripts\\ruff.exe check .`

Closes #119
