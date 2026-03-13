## Why
- `slice 081` restored the last small utility dependency needed by the root `GOSM` hydraulics kernel.
- `GOSM/src/gosm/model/hydraulics.py` is the next coupled hydraulic-growth runtime seam and is required before the full GOSM pipeline can land.
- This slice should stay bounded to the hydraulics kernel itself, the minimal `gosm.model` export surface, and regression coverage; the higher-order pipeline seam remains separate.

## Affected model
- `gosm`
- `src/stomatal_optimiaztion/domains/gosm/model/`
- `tests/`
- architecture status docs

## Validation method
- `poetry run pytest`
- `poetry run ruff check .`
- add coverage for equation tagging, representative hydraulic vector outputs, and turgor-growth derivative outputs

## Comparison target
- legacy `GOSM/src/gosm/model/hydraulics.py`
- current migrated `src/stomatal_optimiaztion/domains/gosm/utils/math.py`
- current migrated `src/stomatal_optimiaztion/domains/gosm/params/defaults.py`
