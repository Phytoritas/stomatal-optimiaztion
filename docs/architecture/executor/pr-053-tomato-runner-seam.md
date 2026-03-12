## Background
- `slice 029` landed the bounded `TomatoModel` surface, but the migrated TOMATO package still lacked the legacy runner seam that turns forcing CSV input into a written results table.
- This PR lands `slice 030` by adding the package-local runner and moving the next architectural uncertainty to the TOMATO partition-policy package.

## Changes
- add the migrated `models/tomato_legacy/run.py` runner over `iter_forcing_csv()`, `TomatoLegacyAdapter`, and `simulate()`
- add runner integration tests for argument parsing, CSV output writing, and module execution
- update architecture artifacts and README so `slice 030` is recorded and `components/partitioning/policy.py` becomes the next blocked seam

## Validation
- `.venv\Scripts\python.exe -m pytest`
- `.venv\Scripts\ruff.exe check .`

## Impact
- the migrated TOMATO `tTHORP` package now has a package-local legacy runner surface
- deeper partition-policy migration remains explicitly blocked and documented for the next slice

## Linked issue
Closes #53
