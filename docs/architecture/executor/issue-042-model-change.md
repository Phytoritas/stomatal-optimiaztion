## Why
- `slice 041` completed the bounded `tTHORP` plotting utilities, so the next TOMATO architectural seam is the `tGOSM` package entry boundary at `src/tgosm/contracts.py`.
- The migrated repo still has no `tGOSM` package surface, so downstream TOMATO model work cannot rely on a canonical contract for optimization requests and results.
- This first `tGOSM` slice should stay contract-first, mirroring the early `tTHORP` migration order and avoiding premature optimizer implementation details.

## Affected model
- `TOMATO tGOSM`
- `src/stomatal_optimiaztion/domains/tomato/tgosm/`
- related TOMATO `tGOSM` contract and import tests

## Validation method
- `poetry run pytest`
- `poetry run ruff check .`
- add coverage for request/result dataclasses, nonnegative clamping, and package import surface

## Comparison target
- legacy `TOMATO/tGOSM/src/tgosm/contracts.py`
- legacy `TOMATO/tGOSM/tests/test_tgosm_contracts.py`
- legacy `TOMATO/tGOSM/tests/test_tgosm_import.py`
