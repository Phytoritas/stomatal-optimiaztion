## Why
- `slice 084` restored the small future-work helper seam, so the next bounded root `GOSM` gap is the alternative stomatal-model comparison layer in `GOSM/src/gosm/model/stomata_models.py`.
- This seam is a direct dependency of the legacy sensitivity analyses and should land before the remaining `instantaneous` and `steady_state` helpers.
- The slice should stay bounded to the public stomatal-model helpers, their shared interpolation utilities, and regression coverage without widening into example scripts.

## Affected model
- `gosm`
- `src/stomatal_optimiaztion/domains/gosm/model/`
- `tests/`
- architecture status docs

## Validation method
- `poetry run pytest`
- `poetry run ruff check .`
- add coverage for equation tagging, interpolation behavior, and representative model output contracts

## Comparison target
- legacy `GOSM/src/gosm/model/stomata_models.py`
- current migrated `src/stomatal_optimiaztion/domains/gosm/model/pipeline.py`
- current migrated `src/stomatal_optimiaztion/domains/gosm/params/defaults.py`
