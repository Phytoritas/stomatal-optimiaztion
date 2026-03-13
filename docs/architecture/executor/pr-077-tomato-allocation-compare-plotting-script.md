## Background
- This PR lands `slice 041` by migrating the TOMATO `tTHORP` repo-level allocation-comparison plotting script.
- The script remains repo-level tooling and continues to treat `matplotlib` as an optional plotting dependency rather than a core package requirement.
- Closing this seam completes the bounded `tTHORP` plotting utilities and moves the next TOMATO architectural uncertainty to the `tGOSM` contracts seam.

## What Changed
- add `scripts/plot_allocation_compare_png.py`
- add regression coverage for allocation-column ingestion, overlap filtering, subsampling, output-path printing, and optional matplotlib error behavior
- update architecture artifacts and README so `slice 041` is recorded and `TOMATO/tGOSM/src/tgosm/contracts.py` becomes the next blocked seam

## Validation
- `poetry run pytest`
- `poetry run ruff check .`

## Impact
- TOMATO `tTHORP` now has both repo-level plotting utilities migrated inside the current repository
- the next TOMATO migration loop can move from `tTHORP` scripts into `tGOSM` package contracts without reopening unresolved plotting assumptions

Closes #77
