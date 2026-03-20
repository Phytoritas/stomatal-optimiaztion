## Why
- `slice 042` opened the `tGOSM` package boundary, so the next bounded TOMATO seam is the placeholder optimizer interface at `src/tgosm/interface.py`.
- The migrated repo now has request/result contracts but still lacks the canonical function that maps optimizer requests to a nonnegative conductance target.
- This slice should keep the implementation intentionally small and placeholder-like, matching the legacy `tGOSM` surface without reopening wider optimizer dependencies yet.

## Affected model
- `TOMATO tGOSM`
- `src/stomatal_optimiaztion/domains/tomato/tomics/flux/`
- related TOMATO `tGOSM` interface tests and package exports

## Validation method
- `poetry run pytest`
- `poetry run ruff check .`
- add coverage for placeholder optimizer behavior, nonnegative target clamping, and package import surface

## Comparison target
- legacy `TOMATO/tGOSM/src/tgosm/interface.py`
- legacy `TOMATO/tGOSM/tests/test_tgosm_contracts.py`
- current migrated `src/stomatal_optimiaztion/domains/tomato/tomics/flux/contracts.py`
