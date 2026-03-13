## Why
- `slice 067` restored the legacy `thorp.model` namespace wrapper, so the remaining bounded THORP compatibility gap is the broadened `THORP/src/thorp/params/__init__.py` import surface.
- The migrated repo already has `THORPParams` and default-bundle builders, but legacy callers still expect `BottomBoundaryCondition`, `SoilHydraulics`, `WeibullVC`, and a flat `default_params()` under `thorp.params`.
- This slice should stay compatibility-bounded: broaden the existing `params.py` exports, lock the legacy import surface with regression coverage, and update architecture records only.

## Affected model
- `thorp`
- `src/stomatal_optimiaztion/domains/thorp/params.py`
- THORP compatibility tests
- architecture docs closing the THORP namespace-wrapper gap

## Validation method
- `poetry run pytest`
- `poetry run ruff check .`
- add coverage for `thorp.params` legacy export identity and flat `default_params()` compatibility

## Comparison target
- legacy `THORP/src/thorp/params/__init__.py`
- legacy `THORP/src/thorp/config.py`
- current migrated `src/stomatal_optimiaztion/domains/thorp/{params.py,defaults.py,soil_hydraulics.py,soil_initialization.py,vulnerability.py}`
