## Why
- `slice 054` opened the bounded `load-cell-data` workflow seam, so the next staged helper surface is the parameter-sweep module at `loadcell_pipeline/sweep.py`.
- The migrated repo now has batch workflow execution, but it still lacks the canonical grid parser, generated-config writer, run collection, and ranking surface used to compare pipeline settings.
- This slice should stay sweep-bounded: grid parsing, config generation, workflow dispatch, run collection, and ranking only.

## Affected model
- `load-cell-data`
- `src/stomatal_optimiaztion/domains/load_cell/`
- related load-cell sweep tests and package exports

## Validation method
- `poetry run pytest`
- `poetry run ruff check .`
- add coverage for grid parsing, generated config validation, run collection, ranking, and sweep orchestration outputs

## Comparison target
- legacy `load-cell-data/loadcell_pipeline/sweep.py`
- current migrated `src/stomatal_optimiaztion/domains/load_cell/workflow.py`
