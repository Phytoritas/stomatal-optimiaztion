## Why
- `slice 053` opened the bounded `load-cell-data` pipeline CLI seam, so the next staged helper surface is the batch workflow module at `loadcell_pipeline/workflow.py`.
- The migrated repo now has package-level pipeline execution, but it still lacks the daily batch runner that organizes environment outputs, per-config result trees, and loadcell-specific artifact writing across interpolated and raw variants.
- This slice should stay workflow-bounded: config signatures, daily file discovery, environment export, substrate join, and batch orchestration only.

## Affected model
- `load-cell-data`
- `src/stomatal_optimiaztion/domains/load_cell/`
- related load-cell workflow tests and package exports

## Validation method
- `poetry run pytest`
- `poetry run ruff check .`
- add coverage for config signature stability, weight-column inference, common-filename filtering, environment export, and workflow orchestration across variants/configs/loadcells

## Comparison target
- legacy `load-cell-data/loadcell_pipeline/workflow.py`
- current migrated `src/stomatal_optimiaztion/domains/load_cell/cli.py`
