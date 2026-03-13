## Why
- `slice 044` opened the TOMATO `tTDGM` contract surface, so the next bounded seam is the placeholder growth-step interface at `src/ttdgm/interface.py`.
- The migrated repo now has the package contracts but still lacks the canonical function that validates allocations and emits an explicit four-organ growth output.
- This slice should stay intentionally small and placeholder-like, matching the legacy `tTDGM` surface without widening into new physiology or shared abstractions.

## Affected model
- `TOMATO tTDGM`
- `src/stomatal_optimiaztion/domains/tomato/ttdgm/`
- related TOMATO `tTDGM` interface tests and package exports

## Validation method
- `poetry run pytest`
- `poetry run ruff check .`
- add coverage for placeholder growth-step behavior, invalid allocation rejection, and package import surface

## Comparison target
- legacy `TOMATO/tTDGM/src/ttdgm/interface.py`
- legacy `TOMATO/tTDGM/tests/test_ttdgm_contracts.py`
- current migrated `src/stomatal_optimiaztion/domains/tomato/ttdgm/contracts.py`
