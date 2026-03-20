## Why
- `slice 035` landed the TOMATO shared scheduler seam, so the next bounded orchestration surface is the dayrun pipeline wrapper at `pipelines/tomato_dayrun.py`.
- The migrated repo still lacks the package-level entry that combines config loading, repo-root resolution, legacy-pipeline execution, deterministic artifact paths, and metadata JSON emission before opening repo-level script entrypoints.

## Affected model
- `TOMATO tTHORP`
- `src/stomatal_optimiaztion/domains/tomato/tomics/alloc/pipelines/`
- related TOMATO dayrun artifact and config-loading integration tests

## Validation method
- `poetry run pytest`
- `poetry run ruff check .`
- add coverage for dayrun artifact writing, relative output-dir resolution, and config-path driven execution

## Comparison target
- legacy `TOMATO/tTHORP/src/tthorp/pipelines/tomato_dayrun.py`
- current migrated TOMATO `core/io.py`, `core/scheduler.py`, and `pipelines/tomato_legacy.py`
