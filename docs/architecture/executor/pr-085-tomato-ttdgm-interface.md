## Summary
- migrate the bounded TOMATO `tTDGM` interface seam into the staged repo package
- expose `run_growth_step()` through the `ttdgm` import surface with placeholder growth behavior intact
- add seam-level regression tests and update architecture records for slice 045

## Validation
- poetry run pytest
- poetry run ruff check .

## Next Seam
- `load-cell-data/loadcell_pipeline/config.py`

Closes #85
