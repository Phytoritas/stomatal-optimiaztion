## Summary
- migrate the bounded `load-cell-data` pipeline CLI seam into the staged `domains/load_cell` package
- preserve parser construction, override mapping, package-level pipeline orchestration, and summary stats behavior
- add seam-level regression tests and update architecture records for slice 053

## Validation
- .\\.venv\\Scripts\\python.exe -m pytest
- .\\.venv\\Scripts\\ruff.exe check .

## Next Seam
- `load-cell-data/loadcell_pipeline/workflow.py`

Closes #101
