## Background
- `slice 035` landed the TOMATO shared scheduler seam, but the migrated repo still lacked the package-level dayrun orchestration surface that writes deterministic artifacts from YAML-configured runs.
- This PR lands `slice 036` by migrating `pipelines/tomato_dayrun.py`, and moves the next TOMATO architectural uncertainty to the repo-level pipeline script seam at `scripts/run_pipeline.py`.

## Changes
- add the migrated TOMATO dayrun pipeline surface with `TomatoDayrunArtifacts`, `run_tomato_dayrun()`, and `run_tomato_dayrun_from_config()`
- export the new dayrun helpers through the package-local `pipelines` and root `tthorp` surfaces
- add seam-level tests for relative and absolute output directories, artifact metadata, and config-path driven execution with inherited YAML configs
- update architecture artifacts and README so `slice 036` is recorded and `scripts/run_pipeline.py` becomes the next blocked seam

## Validation
- `poetry run pytest`
- `poetry run ruff check .`

## Impact
- the migrated TOMATO `tTHORP` package now has a package-level dayrun orchestration surface over the already ported IO, scheduler, and legacy pipeline seams
- repo-level script entrypoints remain explicitly blocked and documented for the next slice

## Linked issue
Closes #67
