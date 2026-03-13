## Why
- `slice 075` migrated the root `GOSM` allometry helper, so the next smallest metabolic seam is `GOSM/src/gosm/model/npp_gpp.py`.
- The NPP/GPP helpers are equation-tagged (`Eq.S8.1`, `Eq.S8.2`) and numerically isolated from the rest of the runtime except for scalar or array inputs.
- This slice should stay bounded to the helper functions, the minimal `gosm.model` namespace export, and regression coverage; larger state or optimization kernels remain for later slices.

## Affected model
- `gosm`
- `src/stomatal_optimiaztion/domains/gosm/model/`
- `tests/`
- architecture status docs

## Validation method
- `poetry run pytest`
- `poetry run ruff check .`
- add coverage for equation tagging, constant target ratio behavior, scalar/vector steady-state ratio behavior, and division edge handling

## Comparison target
- legacy `GOSM/src/gosm/model/npp_gpp.py`
- current migrated `src/stomatal_optimiaztion/domains/gosm/model/__init__.py`
- current migrated `src/stomatal_optimiaztion/domains/gosm/params/defaults.py`
