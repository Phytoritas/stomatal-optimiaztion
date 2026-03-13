## Summary
- migrate the bounded `load-cell-data` IO seam into the staged `domains/load_cell` package
- preserve CSV ingestion, interpolation flags, and single/multi-resolution artifact writing behavior
- add seam-level regression tests and update architecture records for slice 047

## Validation
- poetry run pytest
- poetry run ruff check .

## Next Seam
- `load-cell-data/loadcell_pipeline/aggregation.py`

Closes #89
