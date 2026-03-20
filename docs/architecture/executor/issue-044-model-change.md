## Why
- `slice 043` opened the TOMATO `tGOSM` interface seam, so the next bounded TOMATO source is the `tTDGM` contract surface at `src/ttdgm/contracts.py`.
- The migrated repo currently has no `tomato.ttdgm` package, which blocks later growth-step interface work from landing on a canonical import surface.
- This slice should stay contract-first: dataclasses, allocation validation, and package identity only.

## Affected model
- `TOMATO tTDGM`
- `src/stomatal_optimiaztion/domains/tomato/tomics/grow/`
- related TOMATO `tTDGM` contract tests and package exports

## Validation method
- `poetry run pytest`
- `poetry run ruff check .`
- add coverage for frozen contract dataclasses, allocation validation, and package import identity

## Comparison target
- legacy `TOMATO/tTDGM/src/ttdgm/contracts.py`
- legacy `TOMATO/tTDGM/tests/test_ttdgm_contracts.py`
- legacy `TOMATO/tTDGM/tests/test_ttdgm_import.py`
