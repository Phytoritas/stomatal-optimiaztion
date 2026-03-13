## Why
- `slice 063` restored the stable `thorp.sim.run` wrapper path, so the next smallest remaining THORP compatibility seam is `THORP/src/thorp/equation_registry.py`.
- The migrated repo already has generic traceability helpers, but it still lacks the explicit legacy module path that binds THORP modules and builds the equation-to-callable mapping without caller-provided namespaces.
- This slice should stay compatibility-bounded: module-bound annotated-callable discovery, mapping construction, and regression coverage only.

## Affected model
- `thorp`
- `src/stomatal_optimiaztion/domains/thorp/equation_registry.py`
- THORP traceability compatibility tests
- architecture docs for the next THORP package-surface seam

## Validation method
- `poetry run pytest`
- `poetry run ruff check .`
- add coverage for module-bound annotated-callable discovery and equation-mapping output over migrated THORP modules

## Comparison target
- legacy `THORP/src/thorp/equation_registry.py`
- current migrated `src/stomatal_optimiaztion/domains/thorp/traceability.py`
- current migrated THORP runtime modules with `@implements(...)` annotations
