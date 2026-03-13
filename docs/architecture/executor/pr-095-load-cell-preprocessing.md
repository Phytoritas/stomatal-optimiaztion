## Summary
- migrate the bounded `load-cell-data` preprocessing seam into the staged `domains/load_cell` package
- preserve outlier correction, smoothing, and derivative reconstruction behavior
- add seam-level regression tests and update architecture records for slice 050

## Validation
- .\\.venv\\Scripts\\python.exe -m pytest
- .\\.venv\\Scripts\\ruff.exe check .

## Next Seam
- `load-cell-data/loadcell_pipeline/events.py`

Closes #95
