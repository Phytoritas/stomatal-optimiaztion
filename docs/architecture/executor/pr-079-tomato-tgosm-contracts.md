## Background
- This PR lands `slice 042` by migrating the TOMATO `tGOSM` contracts seam into the staged package layout.
- The repository previously had no `tGOSM` package surface, so downstream TOMATO model work could not rely on a canonical optimizer request/result contract.
- Closing this seam moves the next TOMATO architectural uncertainty to the `tGOSM` interface seam at `src/tgosm/interface.py`.

## What Changed
- add `src/stomatal_optimiaztion/domains/tomato/tgosm/contracts.py` and package exports
- expose `MODEL_NAME == "tGOSM"` and update the root TOMATO domain export surface
- add regression coverage for request/result dataclasses, frozen import identity, and `clamp_nonnegative()`
- update architecture artifacts and README so `slice 042` is recorded and `src/tgosm/interface.py` becomes the next blocked seam

## Validation
- `poetry run pytest`
- `poetry run ruff check .`

## Impact
- TOMATO `tGOSM` now has a canonical contract surface inside the migrated repository
- the next migration loop can add the `tGOSM` interface on top of an explicit package boundary instead of creating that boundary implicitly

Closes #79
