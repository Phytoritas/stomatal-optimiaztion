## Why
- After `slice 080`, the documented next gap was `hydraulics.py`, but that kernel depends directly on `GOSM/src/gosm/utils/math.py`.
- The `polylog2()` helper is a tiny, isolated compatibility seam and is safer to land before the much larger hydraulics kernel.
- This slice should stay bounded to the math helper, the `gosm.utils` export surface, and regression coverage; hydraulics remains the next runtime kernel after this helper lands.

## Affected model
- `gosm`
- `src/stomatal_optimiaztion/domains/gosm/utils/`
- `tests/`
- architecture status docs

## Validation method
- `poetry run pytest`
- `poetry run ruff check .`
- add coverage for scalar and vector `polylog2()` values and exported package surface

## Comparison target
- legacy `GOSM/src/gosm/utils/math.py`
- current migrated `src/stomatal_optimiaztion/domains/gosm/utils/__init__.py`
- upcoming `GOSM/src/gosm/model/hydraulics.py`
