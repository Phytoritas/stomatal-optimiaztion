## Why
- `slice 074` migrated the root `GOSM` radiation kernel, so the next smallest numerical seam is `GOSM/src/gosm/model/allometry.py`.
- The allometry helper is a single equation-tagged function (`Eq.S3.LAI`) with only scalar or array inputs, making it a low-risk continuation slice before larger stateful kernels.
- This slice should stay bounded to the helper itself, the minimal `gosm.model` namespace export, and regression coverage; carbon assimilation, hydraulics, and pipeline orchestration stay for later slices.

## Affected model
- `gosm`
- `src/stomatal_optimiaztion/domains/gosm/model/`
- `tests/`
- architecture status docs

## Validation method
- `poetry run pytest`
- `poetry run ruff check .`
- add coverage for equation tagging, scalar and vector behavior, and a representative baseline snapshot

## Comparison target
- legacy `GOSM/src/gosm/model/allometry.py`
- current migrated `src/stomatal_optimiaztion/domains/gosm/model/radiation.py`
- current migrated `src/stomatal_optimiaztion/domains/gosm/model/__init__.py`
