## Why
- `slice 064` restored the explicit THORP equation-registry module path, so the next smallest namespace-wrapper seam is `THORP/src/thorp/utils/__init__.py`.
- The migrated repo has the underlying traceability and model-card helpers, but it still lacks the legacy convenience import surface that groups them under `thorp.utils`.
- This slice should stay namespace-wrapper-bounded: symbol re-exports, import compatibility regression coverage, and architecture records only.

## Affected model
- `thorp`
- `src/stomatal_optimiaztion/domains/thorp/utils/`
- THORP namespace-wrapper tests
- architecture docs for the next THORP wrapper seam

## Validation method
- `poetry run pytest`
- `poetry run ruff check .`
- add coverage for `thorp.utils` symbol identity over equation registry, implements, and model-card helpers

## Comparison target
- legacy `THORP/src/thorp/utils/__init__.py`
- current migrated `src/stomatal_optimiaztion/domains/thorp/{equation_registry.py,implements.py,model_card.py}`
