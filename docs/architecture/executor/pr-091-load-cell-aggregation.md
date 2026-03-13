## Summary
- migrate the bounded `load-cell-data` aggregation seam into the staged `domains/load_cell` package
- preserve coarse-timescale flux aggregation, daily summary assembly, event counts, and metadata passthrough behavior
- add seam-level regression tests and update architecture records for slice 048

## Validation
- poetry run pytest
- poetry run ruff check .

## Next Seam
- `load-cell-data/loadcell_pipeline/thresholds.py`

Closes #91
