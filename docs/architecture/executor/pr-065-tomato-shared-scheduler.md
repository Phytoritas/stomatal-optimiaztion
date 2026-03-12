## Background
- `slice 034` landed the TOMATO shared IO seam, but the migrated repo still lacked the shared scheduler helpers that derive experiment keys and normalized run schedules.
- This PR lands `slice 035` by migrating `core/scheduler.py`, and moves the next TOMATO architectural uncertainty to the dayrun pipeline seam at `pipelines/tomato_dayrun.py`.

## Changes
- add the migrated TOMATO shared scheduler surface with `build_exp_key()`, `RunSchedule`, and `schedule_from_config()`
- expose the scheduler helpers through the package-local `core` surface
- add seam-level tests for canonical hashing, prefix and digest options, schedule defaults, normalization, and invalid timestep rejection
- update architecture artifacts and README so `slice 035` is recorded and `pipelines/tomato_dayrun.py` becomes the next blocked seam

## Validation
- `poetry run pytest`
- `poetry run ruff check .`

## Impact
- the migrated TOMATO `tTHORP` package now has a deterministic shared scheduler surface for downstream orchestration seams
- `tomato_dayrun` and script entrypoints remain explicitly blocked and documented for the next slice

## Linked issue
Closes #65
