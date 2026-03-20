## Why
- `slice 033` landed the TOMATO package-level legacy pipeline seam, so the next smallest unresolved dependency is the shared config and artifact IO helper at `core/io.py`.
- The migrated repo still lacks a canonical way to create output directories, write metadata JSON, read YAML configs, and resolve `extends` chains before opening `core/scheduler.py` or `pipelines/tomato_dayrun.py`.
- This seam also requires declaring the missing `PyYAML` runtime dependency instead of relying on an undeclared local environment package.

## Affected model
- `TOMATO tTHORP`
- `src/stomatal_optimiaztion/domains/tomato/tomics/alloc/core/`
- related TOMATO config-loading and artifact IO tests

## Validation method
- `poetry run pytest`
- `poetry run ruff check .`
- add coverage for directory creation, JSON writing, YAML parsing, deep merge, and recursive `extends` config loading

## Comparison target
- legacy `TOMATO/tTHORP/src/tthorp/core/io.py`
- current migrated TOMATO pipeline seam and planned `tomato_dayrun` integration path
