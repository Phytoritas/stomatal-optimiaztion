# Module Spec 017: THORP Params Compatibility

## Purpose

Migrate the bounded `THORPParams` seam so the new package can expose a legacy-compatible flat parameter dataclass without undoing the migrated defaults-bundle boundary.

## Source Inputs

- `THORP/src/thorp/config.py` (`THORPParams`)
- migrated defaults bundle in `src/stomatal_optimiaztion/domains/thorp/defaults.py`

## Target Outputs

- `src/stomatal_optimiaztion/domains/thorp/params.py`
- `tests/test_thorp_params.py`

## Responsibilities

1. preserve the legacy flat `THORPParams` field surface for remaining compatibility adapters
2. reuse the migrated defaults bundle instead of duplicating already-migrated seam constants
3. keep forcing metadata passive so the next forcing seam can migrate independently

## Non-Goals

- port `load_forcing` from `forcing.py`
- add `netCDF4` as a runtime dependency
- port simulation orchestration or the full forcing pipeline

## Validation

- `poetry run pytest`
- `poetry run ruff check .`

## Next Seam

- `SimulationOutputs` from `simulate.py`
