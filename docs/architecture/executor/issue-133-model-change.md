## Why
- With `slice 068`, the THORP namespace-wrapper gap is closed, but `GAP-008` remains: current coverage still leans on seam-level unit tests more than package-level smoke checks.
- The repo already has a minimal smoke test, but it does not explicitly lock the migrated THORP package import surface that compatibility callers now rely on.
- This slice should stay validation-bounded: add one package-level smoke check, record the resulting coverage note, and update architecture status only.

## Affected model
- `thorp`
- `tests/test_smoke.py`
- `docs/architecture/review/`
- architecture status docs

## Validation method
- `poetry run pytest`
- `poetry run ruff check .`
- extend smoke coverage for package-level THORP imports and document what remains out of scope

## Comparison target
- current migrated `src/stomatal_optimiaztion/domains/thorp/__init__.py`
- existing repo smoke validation baseline
