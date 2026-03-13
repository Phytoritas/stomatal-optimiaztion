## Why
- `slice 070` closed the THORP and load-cell architecture gaps, but the root legacy `GOSM/` and `TDGM/` packages under `00. Stomatal Optimization` were not yet opened as migrated domains.
- The smallest missing root `GOSM` seam is the model-card and traceability foundation: package import surface, packaged model-card JSON access, and `@implements(...)` metadata helpers.
- This slice should stay architecture-bounded: open `domains.gosm` with model-card and traceability utilities only, record the new wave in the architecture spine, and leave numerical runtime seams for follow-up slices.

## Affected model
- `gosm`
- `src/stomatal_optimiaztion/domains/gosm/`
- `src/stomatal_optimiaztion/domains/__init__.py`
- `tests/`
- architecture status docs

## Validation method
- `poetry run pytest`
- `poetry run ruff check .`
- add coverage for packaged GOSM model-card access, equation-id validation, traceability metadata helpers, and root domain import surface stability

## Comparison target
- legacy `GOSM/model_card/C001.json` through `GOSM/model_card/C010.json`
- legacy `GOSM/src/gosm/utils/traceability.py`
- legacy `GOSM/src/gosm/__init__.py`
