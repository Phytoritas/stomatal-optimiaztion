## Background
- This PR lands `slice 043` by migrating the TOMATO `tGOSM` interface seam into the staged package layout.
- The repository already had `tGOSM` request/result contracts, but it still lacked the canonical placeholder optimizer entrypoint that downstream TOMATO flows can call.
- Closing this seam moves the next TOMATO architectural uncertainty to the `tTDGM` contracts seam at `src/ttdgm/contracts.py`.

## What Changed
- add `src/stomatal_optimiaztion/domains/tomato/tgosm/interface.py`
- export `run_stomatal_optimization()` through the staged `tgosm` package
- add regression coverage for placeholder optimizer behavior, nonnegative target clamping, and explicit WUE/objective placeholders
- update architecture artifacts and README so `slice 043` is recorded and `src/ttdgm/contracts.py` becomes the next blocked seam

## Validation
- `poetry run pytest`
- `poetry run ruff check .`

## Impact
- TOMATO `tGOSM` now has both a canonical contract surface and a minimal callable interface inside the migrated repository
- the next migration loop can step into `tTDGM` with the same contract/interface-first pattern already established for sibling TOMATO packages

Closes #81
