## Summary
- migrate the bounded `load-cell-data` config seam into a new staged `domains/load_cell` package
- preserve `PipelineConfig` defaults plus YAML loading, override precedence, and path coercion behavior
- add seam-level regression tests and update architecture records for slice 046

## Validation
- poetry run pytest
- poetry run ruff check .

## Next Seam
- `load-cell-data/loadcell_pipeline/io.py`

Closes #87
