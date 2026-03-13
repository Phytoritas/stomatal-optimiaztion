## Summary
- migrate the bounded `load-cell-data` sweep seam into the staged `domains/load_cell` package
- preserve grid parsing, generated config emission, workflow dispatch, run collection, and ranking behavior
- add seam-level regression tests and update architecture records for slice 055

## Validation
- .\\.venv\\Scripts\\python.exe -m pytest
- .\\.venv\\Scripts\\ruff.exe check .

## Next Seam
- `load-cell-data/loadcell_pipeline/run_all.py`

Closes #105
