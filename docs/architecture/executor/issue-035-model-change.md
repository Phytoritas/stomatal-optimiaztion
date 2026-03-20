## Why
- `slice 034` landed the TOMATO shared IO seam, so the next smallest unresolved dependency is the shared scheduling helper at `core/scheduler.py`.
- The migrated repo still lacks a canonical way to derive deterministic experiment keys and normalized run schedules from config payloads before opening `pipelines/tomato_dayrun.py` or repo-level script entrypoints.

## Affected model
- `TOMATO tTHORP`
- `src/stomatal_optimiaztion/domains/tomato/tomics/alloc/core/`
- related TOMATO scheduling and config-derived run-shape tests

## Validation method
- `poetry run pytest`
- `poetry run ruff check .`
- add coverage for experiment-key determinism, payload hashing options, default schedule behavior, and invalid `default_dt_s` rejection

## Comparison target
- legacy `TOMATO/tTHORP/src/tthorp/core/scheduler.py`
- current migrated TOMATO `core/io.py` and package-level legacy pipeline seams
