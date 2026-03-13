## Why
- `slice 089` restored the PTM kernel, so the next bounded dependency is `TDGM/src/tdgm/coupling.py`.
- The coupling helpers are required before the root `TDGM` equation registry and THORP-G postprocess seams can land.
- The slice should stay bounded to THORP-G coupling primitives, package exports, and regression coverage without widening into registry assembly or MATLAB postprocess IO.

## Affected model
- `tdgm`
- `src/stomatal_optimiaztion/domains/tdgm/`
- `tests/`
- architecture status docs

## Validation method
- `poetry run pytest`
- `poetry run ruff check .`
- add coverage for the `Eq.S.3.*` coupling helpers, the one-step coupling wrapper, and allocation-history smoothing

## Comparison target
- legacy `TDGM/src/tdgm/coupling.py`
- current migrated `src/stomatal_optimiaztion/domains/tdgm/` package foundation plus PTM/turgor seams
- root `TDGM` model-card assets
