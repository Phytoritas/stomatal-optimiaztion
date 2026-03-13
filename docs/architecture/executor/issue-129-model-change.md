## Why
- `slice 066` restored the legacy `thorp.io` namespace wrapper, so the next bounded THORP compatibility seam is `THORP/src/thorp/model/__init__.py`.
- The migrated repo already exposes the underlying allocation, growth, hydraulics, radiation, and soil helpers, but callers that import them through `thorp.model` still do not have a stable namespace path.
- This slice should stay namespace-wrapper-bounded: grouped re-exports, import compatibility regression coverage, and architecture records only.

## Affected model
- `thorp`
- `src/stomatal_optimiaztion/domains/thorp/model/`
- THORP namespace-wrapper tests
- architecture docs for the next THORP wrapper seam

## Validation method
- `poetry run pytest`
- `poetry run ruff check .`
- add coverage for `thorp.model` symbol identity over allocation, growth, hydraulics, radiation, and soil helpers

## Comparison target
- legacy `THORP/src/thorp/model/__init__.py`
- current migrated `src/stomatal_optimiaztion/domains/thorp/{allocation.py,growth.py,hydraulics.py,radiation.py,soil_initialization.py,soil_dynamics.py}`
