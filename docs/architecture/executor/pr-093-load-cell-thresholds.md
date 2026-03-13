## Summary
- migrate the bounded `load-cell-data` thresholds seam into the staged `domains/load_cell` package
- preserve adaptive irrigation/drainage threshold estimation, valid-mask fallback, and sign constraints
- add seam-level regression tests and update architecture records for slice 049

## Validation
- poetry run pytest
- poetry run ruff check .

## Next Seam
- `load-cell-data/loadcell_pipeline/preprocessing.py`

Closes #93
