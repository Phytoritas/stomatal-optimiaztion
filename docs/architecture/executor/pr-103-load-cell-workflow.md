## Summary
- migrate the bounded `load-cell-data` workflow seam into the staged `domains/load_cell` package
- preserve config signatures, daily environment export, per-variant result-tree writing, and substrate-sensor joins
- add seam-level regression tests and update architecture records for slice 054

## Validation
- .\\.venv\\Scripts\\python.exe -m pytest
- .\\.venv\\Scripts\\ruff.exe check .

## Next Seam
- `load-cell-data/loadcell_pipeline/sweep.py`

Closes #103
