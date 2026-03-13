## Summary
- migrate the bounded `load-cell-data` events seam into the staged `domains/load_cell` package
- preserve derivative labeling, hysteresis labeling, event grouping, and close-event merge behavior
- add seam-level regression tests and update architecture records for slice 051

## Validation
- .\\.venv\\Scripts\\python.exe -m pytest
- .\\.venv\\Scripts\\ruff.exe check .

## Next Seam
- `load-cell-data/loadcell_pipeline/fluxes.py`

Closes #97
