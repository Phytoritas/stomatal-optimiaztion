## Why
- `slice 071` opened the root `GOSM` package foundation and `slice 072` opened the parallel root `TDGM` foundation, so the next earliest numerical seam is the root `GOSM` parameter-defaults bundle.
- Later GOSM runtime modules already depend on `BaselineInputs.matlab_default()`, legacy alias properties, and bundled callable parameter functions, so this seam is the narrowest stable entry into the numerical port.
- This slice should stay bounded: migrate the defaults dataclass and package surface only, then leave `gosm.model` runtime kernels for later slices.

## Affected model
- `gosm`
- `src/stomatal_optimiaztion/domains/gosm/params/`
- `src/stomatal_optimiaztion/domains/gosm/__init__.py`
- `tests/`
- architecture status docs

## Validation method
- `poetry run pytest`
- `poetry run ruff check .`
- add coverage for `BaselineInputs.matlab_default()`, legacy alias properties, callable parameter functions, and package import surface stability

## Comparison target
- legacy `GOSM/src/gosm/params/defaults.py`
- legacy `GOSM/src/gosm/params/__init__.py`
- current migrated `src/stomatal_optimiaztion/domains/gosm/`
