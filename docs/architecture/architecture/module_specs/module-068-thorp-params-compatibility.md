# Module Spec 068: THORP Params Compatibility

## Purpose

Broaden the migrated `thorp.params` module so legacy callers can recover the grouped compatibility surface that previously came from `THORP/src/thorp/params/__init__.py`.

## Source Inputs

- `THORP/src/thorp/params/__init__.py`
- `THORP/src/thorp/config.py`

## Target Outputs

- `src/stomatal_optimiaztion/domains/thorp/params.py`
- `tests/test_thorp_params_compatibility.py`

## Responsibilities

1. preserve the legacy `thorp.params` exports for `BottomBoundaryCondition`, `SoilHydraulics`, `THORPParams`, `WeibullVC`, and flat `default_params()`
2. preserve symbol identity for migrated primitive types instead of redefining them
3. keep the seam compatibility-bounded instead of redesigning the internal THORP defaults bundle

## Non-Goals

- redesign `defaults.py` or the root `domains.thorp` export surface
- reintroduce the legacy `config.py` module layout
- widen the slice into package-level smoke validation or shared utility design notes

## Validation

- `poetry run pytest`
- `poetry run ruff check .`

## Next Artifact

- THORP package-level smoke validation note
