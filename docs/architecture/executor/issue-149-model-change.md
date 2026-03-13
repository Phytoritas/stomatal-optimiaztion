## Why
- `slice 076` migrated the root `GOSM` NPP/GPP helpers, so the next bounded objective-layer seam is `GOSM/src/gosm/model/optimal_control.py`.
- The optimal-control helpers are equation-tagged (`Eq.S2.1` through `Eq.S2.6`) and remain numerically isolated from the rest of the runtime except for scalar or array inputs.
- This slice should stay bounded to the helper functions, the minimal `gosm.model` namespace export, and regression coverage; carbon-dynamics, conductance-temperature, and full pipeline seams remain for later slices.

## Affected model
- `gosm`
- `src/stomatal_optimiaztion/domains/gosm/model/`
- `tests/`
- architecture status docs

## Validation method
- `poetry run pytest`
- `poetry run ruff check .`
- add coverage for equation tagging, objective accumulation, eta/chi/theta helper behavior, and vectorized derivative propagation

## Comparison target
- legacy `GOSM/src/gosm/model/optimal_control.py`
- current migrated `src/stomatal_optimiaztion/domains/gosm/model/__init__.py`
- current migrated `src/stomatal_optimiaztion/domains/gosm/model/npp_gpp.py`
