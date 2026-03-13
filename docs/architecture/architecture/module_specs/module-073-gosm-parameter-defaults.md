# Module Spec 073: GOSM Parameter Defaults

## Purpose

Open the first bounded root `GOSM/` numerical seam by restoring the parameter-defaults bundle that later runtime kernels already depend on.

## Source Inputs

- `GOSM/src/gosm/params/defaults.py`
- `GOSM/src/gosm/params/__init__.py`

## Target Outputs

- `src/stomatal_optimiaztion/domains/gosm/params/`
- `src/stomatal_optimiaztion/domains/gosm/__init__.py`
- `tests/test_gosm_params_defaults.py`

## Responsibilities

1. preserve `BaselineInputs.matlab_default()` over the legacy MATLAB baseline constants
2. preserve legacy alias properties used by later ports
3. preserve bundled callable parameter functions with vectorized `numpy` behavior

## Non-Goals

- migrate runtime kernels under `GOSM/src/gosm/model/`
- migrate example adapters or scripts
- widen into root `TDGM` runtime seams

## Validation

- `poetry run pytest`
- `poetry run ruff check .`

## Next Seam

- `GOSM/src/gosm/model/radiation.py`
