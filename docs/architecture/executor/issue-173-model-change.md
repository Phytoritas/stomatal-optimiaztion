## Why
- `slice 088` opened the first numerical root `TDGM` seam, so the next bounded runtime dependency is the PTM kernel in `TDGM/src/tdgm/ptm.py`.
- The PTM kernel is a prerequisite for the larger coupling, equation-registry, and THORP-G postprocess seams.
- The slice should stay bounded to the PTM helpers, package exports, and regression coverage without widening into coupling or THORP-G tooling.

## Affected model
- `tdgm`
- `src/stomatal_optimiaztion/domains/tdgm/`
- `tests/`
- architecture status docs

## Validation method
- `poetry run pytest`
- `poetry run ruff check .`
- add coverage for equation tagging, viscosity helper behavior, and representative PTM concentration outputs

## Comparison target
- legacy `TDGM/src/tdgm/ptm.py`
- current migrated `src/stomatal_optimiaztion/domains/tdgm/` package foundation
- root `TDGM` model-card assets
