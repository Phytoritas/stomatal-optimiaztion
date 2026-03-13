## Why
- `slice 078` migrated the root `GOSM` carbon-dynamics helpers, so the next bounded coupled runtime seam is `GOSM/src/gosm/model/conductance_temperature.py`.
- The conductance-temperature kernel carries the first iterative Newton solve in the root `GOSM` runtime and emits multiple coupled vectors that downstream assimilation and pipeline seams depend on.
- This slice should stay bounded to the kernel itself, the minimal `gosm.model` namespace export, and regression coverage; hydraulics, carbon assimilation, and full pipeline orchestration remain for later slices.

## Affected model
- `gosm`
- `src/stomatal_optimiaztion/domains/gosm/model/`
- `tests/`
- architecture status docs

## Validation method
- `poetry run pytest`
- `poetry run ruff check .`
- add coverage for equation tagging, representative baseline vector outputs, latent-heat calculation, and coupled derivative propagation

## Comparison target
- legacy `GOSM/src/gosm/model/conductance_temperature.py`
- current migrated `src/stomatal_optimiaztion/domains/gosm/model/radiation.py`
- current migrated `src/stomatal_optimiaztion/domains/gosm/params/defaults.py`
