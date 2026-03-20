## Background
- This PR lands `slice 039` by migrating the TOMATO `tTHORP` THORP reference adapter seam into the staged package layout.
- The legacy adapter depended on external THORP source discovery, but the current repository already contains a migrated `domains.thorp` runtime surface.
- Closing this seam moves the next TOMATO architectural uncertainty to the repo-level simulation plotting script at `scripts/plot_simulation_png.py`.

## What Changed
- add `src/stomatal_optimiaztion/domains/tomato/tomics/alloc/models/thorp_ref/adapter.py` and package exports
- bind the adapter to migrated THORP defaults and `run()` instead of external source-path probing
- add regression coverage for forcing normalization, empty-output handling, and a smoke path against the migrated THORP runtime
- update architecture artifacts and README so `slice 039` is recorded and `scripts/plot_simulation_png.py` becomes the next blocked seam

## Validation
- `poetry run pytest`
- `poetry run ruff check .`

## Impact
- TOMATO `tTHORP` now has both the legacy tomato bridge and the THORP reference bridge inside the migrated repository
- downstream TOMATO work can compare legacy and THORP-reference outputs without depending on a separate THORP checkout

Closes #73
