## Background
- This PR lands `slice 040` by migrating the TOMATO `tTHORP` repo-level simulation plotting script.
- The script is kept as repo-level tooling and continues to treat `matplotlib` as an optional plotting dependency rather than a core package requirement.
- Closing this seam moves the next TOMATO architectural uncertainty to the allocation-comparison plotting script at `scripts/plot_allocation_compare_png.py`.

## What Changed
- add `scripts/plot_simulation_png.py`
- add regression coverage for CLI parsing, CSV subsampling, output-path printing, and optional matplotlib error behavior
- update architecture artifacts and README so `slice 040` is recorded and `scripts/plot_allocation_compare_png.py` becomes the next blocked seam

## Validation
- `poetry run pytest`
- `poetry run ruff check .`

## Impact
- TOMATO `tTHORP` now has a migrated repo-level plotting entrypoint for simulation summary PNG generation
- downstream review of legacy-vs-migrated outputs can reuse one bounded plotting utility without introducing plotting dependencies into the core runtime

Closes #75
