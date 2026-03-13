## Why
- `slice 071` reopened the root legacy model wave by landing `domains.gosm`, but the parallel root `TDGM/` package is still absent from the migrated repo.
- The smallest missing root `TDGM` seam is the same foundation surface: packaged model-card JSON access, equation-id validation, and traceability metadata helpers.
- This slice should stay architecture-bounded: open `domains.tdgm` with model-card and traceability utilities only, then leave PTM, turgor-growth, and coupling runtimes for follow-up slices.

## Affected model
- `tdgm`
- `src/stomatal_optimiaztion/domains/tdgm/`
- `src/stomatal_optimiaztion/domains/__init__.py`
- `tests/`
- architecture status docs

## Validation method
- `poetry run pytest`
- `poetry run ruff check .`
- add coverage for packaged TDGM model-card access, equation-id validation, traceability metadata helpers, and root domain import surface stability

## Comparison target
- legacy `TDGM/model_card/C001.json` through `TDGM/model_card/C006.json`
- legacy `TDGM/src/tdgm/implements.py`
- legacy `TDGM/src/tdgm/__init__.py`
