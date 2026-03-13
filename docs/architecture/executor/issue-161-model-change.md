## Why
- `slice 082` migrated the root `GOSM` hydraulics kernel, so the next bounded seam is the fully wired runtime pipeline in `GOSM/src/gosm/model/pipeline.py`.
- All direct dependencies of the pipeline are now present in the migrated repo: radiation, hydraulics, conductance-temperature, and carbon-assimilation.
- This slice should stay bounded to the pipeline wrapper, the minimal `gosm.model` export surface, and regression coverage; policy layers and examples remain later seams.

## Affected model
- `gosm`
- `src/stomatal_optimiaztion/domains/gosm/model/`
- `tests/`
- architecture status docs

## Validation method
- `poetry run pytest`
- `poetry run ruff check .`
- add coverage for equation tagging, representative pipeline outputs, and output contract shape

## Comparison target
- legacy `GOSM/src/gosm/model/pipeline.py`
- current migrated runtime kernels under `src/stomatal_optimiaztion/domains/gosm/model/`
- current migrated `src/stomatal_optimiaztion/domains/gosm/params/defaults.py`
