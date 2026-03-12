## Background
- `slice 032` closed the TOMATO partitioning package, but the migrated repo still lacked the package-level legacy pipeline wrapper that turns config payloads and forcing CSV paths into a default tomato simulation run.
- This PR lands `slice 033` by migrating `pipelines/tomato_legacy.py`, and moves the next TOMATO architectural uncertainty to the shared `core/io.py` seam.

## Changes
- add the migrated TOMATO pipeline package with repo-root resolution, forcing-path resolution, filtered config payload helpers, pipeline execution, and metrics summaries
- export the new pipeline helpers through the package-local `tthorp` surface
- add path-resolution, pipeline-run, and summary-metric tests for the migrated package-level legacy pipeline seam
- update architecture artifacts and README so `slice 033` is recorded and `core/io.py` becomes the next blocked seam

## Validation
- `.venv\Scripts\python.exe -m pytest`
- `.venv\Scripts\ruff.exe check .`

## Impact
- the migrated TOMATO `tTHORP` package now has a config-driven package-level legacy pipeline surface
- deeper shared IO and dayrun orchestration remain explicitly blocked and documented for the next slice

## Linked issue
Closes #61
