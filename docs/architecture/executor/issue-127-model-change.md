## Why
- `slice 065` restored the legacy `thorp.utils` namespace wrapper, so the next bounded THORP compatibility seam is `THORP/src/thorp/io/__init__.py`.
- The migrated repo already exposes `Forcing`, `load_forcing()`, `load_mat()`, and `save_mat()`, but callers that import them through `thorp.io` still do not have a stable namespace path.
- This slice should stay namespace-wrapper-bounded: grouped re-exports, import compatibility regression coverage, and architecture records only.

## Affected model
- `thorp`
- `src/stomatal_optimiaztion/domains/thorp/io/`
- THORP namespace-wrapper tests
- architecture docs for the next THORP wrapper seam

## Validation method
- `poetry run pytest`
- `poetry run ruff check .`
- add coverage for `thorp.io` symbol identity over forcing and MATLAB I/O helpers

## Comparison target
- legacy `THORP/src/thorp/io/__init__.py`
- current migrated `src/stomatal_optimiaztion/domains/thorp/{forcing.py,matlab_io.py}`
