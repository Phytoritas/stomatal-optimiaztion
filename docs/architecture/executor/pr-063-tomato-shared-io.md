## Background
- `slice 033` landed the TOMATO package-level legacy pipeline seam, but the migrated repo still lacked the shared IO helpers that load YAML configs and write deterministic artifact metadata.
- This PR lands `slice 034` by migrating `core/io.py`, and moves the next TOMATO architectural uncertainty to the shared `core/scheduler.py` seam.

## Changes
- add the migrated TOMATO `core` package with directory creation, JSON writing, YAML parsing, recursive deep merge, and `extends`-chain config loading
- declare `PyYAML` as an explicit runtime dependency and refresh the Poetry lockfile
- add seam-level tests for shared IO behavior and config inheritance
- update architecture artifacts and README so `slice 034` is recorded and `core/scheduler.py` becomes the next blocked seam

## Validation
- `poetry run pytest`
- `poetry run ruff check .`

## Impact
- the migrated TOMATO `tTHORP` package now has a clean-environment config and artifact IO surface
- scheduler and dayrun orchestration remain explicitly blocked and documented for the next slice

## Linked issue
Closes #63
