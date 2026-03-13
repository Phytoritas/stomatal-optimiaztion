## Why
- `slice 090` restored the TDGM coupling helpers, so the next bounded dependency is the package-level registry in `TDGM/src/tdgm/equation_registry.py`.
- The registry is required to assemble traceability coverage across the migrated PTM, turgor-growth, and coupling seams before THORP-G postprocess lands.
- The slice should stay bounded to registry assembly, regression coverage, and architecture-status updates without widening into postprocess IO.

## Affected model
- `tdgm`
- `src/stomatal_optimiaztion/domains/tdgm/`
- `tests/`
- architecture status docs

## Validation method
- `poetry run pytest`
- `poetry run ruff check .`
- add coverage for migrated-callable discovery and equation-to-callable grouping across PTM, turgor-growth, and coupling modules

## Comparison target
- legacy `TDGM/src/tdgm/equation_registry.py`
- current migrated `src/stomatal_optimiaztion/domains/tdgm/` runtime seams
- root `TDGM` model-card assets
