# Module Spec: Slice 103 TDGM THORP-G Rerun Parity

## Goal

Close the missing root `TDGM` rerun gap by restoring the legacy `tdgm.thorp_g` runtime surface and validating current Python reruns against the original MATLAB THORP-G `.mat` outputs.

## Source

- `TDGM/src/tdgm/thorp_g/*.py`
- `TDGM/tests/test_thorp_g_v14_regression_cases_first_2_weeks.py`
- legacy THORP-G `.mat` payloads under `TDGM/example/Supplementary Code __THORP_code_v1.4/Simulations_and_code_to_plot/`

## Target

- `src/stomatal_optimiaztion/domains/tdgm/thorp_g/`
- `src/stomatal_optimiaztion/domains/tdgm/coupling.py`
- `src/stomatal_optimiaztion/domains/tdgm/__init__.py`
- `tests/test_tdgm_thorp_g_rerun_parity.py`
- `tests/test_tdgm_coupling.py`

## Requirements

1. restore the legacy `tdgm.thorp_g` package-level runtime contract:
   - `default_params()`
   - `load_forcing()`
   - `run()`
   - MAT I/O compatibility
2. wire the package to the current repo namespace without reintroducing a separate legacy project
3. compare ten representative THORP-G rerun scenarios against the real MATLAB `.mat` outputs for the first three stored points
4. expose the missing mean-allocation update helper through the shared root `tdgm.coupling` surface

## Non-Goals

- full-horizon TDGM THORP-G reruns
- new TDGM figure workflows beyond the already migrated Plotkit bundles
- designing a new general-purpose TDGM configuration system

## Validation

1. `python -m pytest tests/test_tdgm_thorp_g_rerun_parity.py`
2. keep `tests/test_tdgm_coupling.py` green
3. keep repo-wide `pytest` and `ruff` green
