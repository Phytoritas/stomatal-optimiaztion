## Why
- `slice 079` migrated the root `GOSM` conductance-temperature kernel, so the next bounded coupled runtime seam is `GOSM/src/gosm/model/carbon_assimilation.py`.
- The carbon-assimilation kernel is the next biochemical step after the conductance solve and emits `a_n`, `r_d`, and `lambda_wue`, which are required by later control and pipeline seams.
- This slice should stay bounded to the kernel itself, the minimal `gosm.model` namespace export, and regression coverage; hydraulics and the full pipeline seam remain for later slices.

## Affected model
- `gosm`
- `src/stomatal_optimiaztion/domains/gosm/model/`
- `tests/`
- architecture status docs

## Validation method
- `poetry run pytest`
- `poetry run ruff check .`
- add coverage for equation tagging, representative baseline vector outputs, zero-conductance behavior, and marginal-WUE stability

## Comparison target
- legacy `GOSM/src/gosm/model/carbon_assimilation.py`
- current migrated `src/stomatal_optimiaztion/domains/gosm/model/conductance_temperature.py`
- current migrated `src/stomatal_optimiaztion/domains/gosm/params/defaults.py`
