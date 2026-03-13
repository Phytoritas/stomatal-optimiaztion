# THORP Package-Level Smoke Validation Note

## Purpose

Record the minimum package-level smoke coverage now that the THORP runtime and compatibility wrappers are migrated.

## Covered Surface

- root `stomatal_optimiaztion.domains.thorp` import surface
- compatibility wrapper packages `thorp.io`, `thorp.model`, and `thorp.utils`
- broadened `thorp.params.default_params()` flat legacy bundle
- curated `model_card` inventory presence

## Validation Hook

- `tests/test_smoke.py::test_smoke`
- `tests/test_smoke.py::test_thorp_package_import_surface_smoke`
- `.\.venv\Scripts\python.exe -m pytest`
- `.\.venv\Scripts\ruff.exe check .`

## Out Of Scope

- full THORP numerical regression coverage beyond the already migrated seam tests
- long-running forcing-driven simulations
- TOMATO or `load-cell-data` package-level smoke expansion

## Result

The repo now has one package-level smoke check that exercises the migrated THORP root import surface and the restored compatibility wrappers together, reducing the risk that wrapper-level breakage escapes the seam-level test suite.
