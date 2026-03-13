## Summary
- migrate the bounded `load-cell-data` flux-decomposition seam into the staged `domains/load_cell` package
- preserve irrigation/drainage/transpiration splitting, event-gap transpiration interpolation, and water-balance scaling behavior
- add seam-level regression tests and update architecture records for slice 052

## Validation
- .\\.venv\\Scripts\\python.exe -m pytest
- .\\.venv\\Scripts\\ruff.exe check .

## Next Seam
- `load-cell-data/loadcell_pipeline/cli.py`

Closes #99
