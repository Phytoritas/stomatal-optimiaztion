## Why
- `slice 077` migrated the root `GOSM` optimal-control helpers, so the next bounded carbon-balance seam is `GOSM/src/gosm/model/carbon_dynamics.py`.
- The carbon-dynamics helpers are equation-tagged (`Eq.S1.1` through `Eq.S1.9`) and remain numerically isolated from the rest of the runtime except for `BaselineInputs` plus scalar or array inputs.
- This slice should stay bounded to the helper functions, the minimal `gosm.model` namespace export, and regression coverage; conductance-temperature, hydraulics, and pipeline seams remain for later slices.

## Affected model
- `gosm`
- `src/stomatal_optimiaztion/domains/gosm/model/`
- `tests/`
- architecture status docs

## Validation method
- `poetry run pytest`
- `poetry run ruff check .`
- add coverage for equation tagging, baseline respiration and growth helpers, NSC limitation behavior, and compact/full NSC rate snapshots

## Comparison target
- legacy `GOSM/src/gosm/model/carbon_dynamics.py`
- current migrated `src/stomatal_optimiaztion/domains/gosm/model/__init__.py`
- current migrated `src/stomatal_optimiaztion/domains/gosm/params/defaults.py`
