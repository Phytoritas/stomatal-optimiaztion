## Why
- `slice 028` left `models/tomato_legacy/tomato_model.py` blocked, so the migrated adapter still needs an injected `model_factory` for end-to-end execution.
- The next bounded seam should migrate the legacy tomato model surface that owns reset-state defaults, forcing-row ingestion, output payload shape, and default adapter construction without opening broad pipeline or CLI work.

## Affected model
- `TOMATO tTHORP`
- `src/stomatal_optimiaztion/domains/tomato/tthorp/models/tomato_legacy/tomato_model.py`
- related TOMATO `tTHORP` tests and architecture slice records

## Validation method
- `poetry run pytest`
- `poetry run ruff check .`
- add behavior-preserving model-state checks for reset defaults, forcing-row mapping, output payload shape, density updates, and default adapter execution

## Comparison target
- legacy `TOMATO/tTHORP/src/tthorp/models/tomato_legacy/tomato_model.py`
- current slice 028 adapter behavior and documented TOMATO `tTHORP` architecture scope
