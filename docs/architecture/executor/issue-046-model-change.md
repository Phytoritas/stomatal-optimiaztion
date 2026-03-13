## Why
- `slice 045` completed the bounded TOMATO `tTDGM` interface seam, so the next unresolved domain boundary is the first `load-cell-data` config/helper surface at `loadcell_pipeline/config.py`.
- The migrated repo currently has no `load_cell` package, which blocks later preprocessing, workflow, and CLI seams from landing on a canonical package surface.
- This slice should stay config-first: dataclass defaults, path coercion, YAML loading, and override behavior only.

## Affected model
- `load-cell-data`
- `src/stomatal_optimiaztion/domains/load_cell/`
- related load-cell config tests and domain exports

## Validation method
- `poetry run pytest`
- `poetry run ruff check .`
- add coverage for config defaults, `Path` serialization, YAML loading, override precedence, and invalid config file behavior

## Comparison target
- legacy `load-cell-data/loadcell_pipeline/config.py`
- current repo architecture docs for the `domains/load_cell` target layout
