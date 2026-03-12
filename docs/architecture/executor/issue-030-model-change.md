## Why
- `slice 029` landed the bounded `TomatoModel` surface, so the next smallest blocked TOMATO seam is the legacy `models/tomato_legacy/run.py` runner.
- The migrated package still lacks a package-local runner that binds forcing CSV ingestion, default adapter construction, argument parsing, and CSV result writing into one bounded execution surface.

## Affected model
- `TOMATO tTHORP`
- `src/stomatal_optimiaztion/domains/tomato/tthorp/models/tomato_legacy/run.py`
- related TOMATO `tTHORP` tests and architecture slice records

## Validation method
- `poetry run pytest`
- `poetry run ruff check .`
- add runner-focused checks for argument parsing, adapter invocation, output path creation, and module execution behavior

## Comparison target
- legacy `TOMATO/tTHORP/src/tthorp/models/tomato_legacy/run.py`
- current migrated `forcing_csv`, `adapter`, and `TomatoModel` seams
