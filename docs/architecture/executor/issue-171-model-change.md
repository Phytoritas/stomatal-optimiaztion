## Why
- root `GOSM` helper wave is now closed through `slice 087`, so the next bounded architecture gap is the first numerical root `TDGM` kernel in `TDGM/src/tdgm/turgor_growth.py`.
- This seam is the smallest runtime entry into root `TDGM` and should land before the larger PTM, coupling, and THORP-G postprocess seams.
- The slice should stay bounded to the turgor-driven growth kernel, package exports, and regression coverage without widening into PTM or coupling logic.

## Affected model
- `tdgm`
- `src/stomatal_optimiaztion/domains/tdgm/`
- `tests/`
- architecture status docs

## Validation method
- `poetry run pytest`
- `poetry run ruff check .`
- add coverage for equation tagging, scalar/vector behavior, and representative growth outputs

## Comparison target
- legacy `TDGM/src/tdgm/turgor_growth.py`
- current migrated `src/stomatal_optimiaztion/domains/tdgm/` package foundation
- root `TDGM` model-card assets
