# Module Spec: Slice 102 GOSM Python Rerun Parity

## Goal

Restore the legacy root `GOSM` rerun helpers and validate the migrated Python kernels against the original MATLAB example `.mat` outputs.

## Source

- `GOSM/src/gosm/examples/control.py`
- `GOSM/src/gosm/examples/sensitivity.py`
- `GOSM/tests/test_regression_example_control.py`
- `GOSM/tests/test_regression_sensitivity_environmental_conditions.py`
- `GOSM/tests/test_regression_sensitivity_p_soil_min_conductance_loss.py`
- legacy example `.mat` payloads under `GOSM/example/`

## Target

- `src/stomatal_optimiaztion/domains/gosm/examples/control.py`
- `src/stomatal_optimiaztion/domains/gosm/examples/sensitivity.py`
- `src/stomatal_optimiaztion/domains/gosm/examples/__init__.py`
- `tests/test_gosm_rerun_control.py`
- `tests/test_gosm_rerun_sensitivity_environmental_conditions.py`
- `tests/test_gosm_rerun_sensitivity_p_soil_min.py`

## Requirements

1. expose the legacy `run_control_plot_data()` rerun surface over the migrated root `gosm.model` kernels
2. expose the legacy sensitivity rerun surfaces for:
   - `RH`
   - `c_a`
   - `P_soil`
   - `P_soil_min`
3. compare the Python rerun outputs directly against the real legacy MATLAB `.mat` payloads
4. keep the slow `imag` conductance-loss branch available but opt-in so default repo validation stays bounded

## Non-Goals

- replacing the already migrated Plotkit figure workflows
- pixel-level figure comparison
- broadening the root `GOSM` runtime beyond the already migrated kernels

## Validation

1. `python -m pytest tests/test_gosm_rerun_control.py tests/test_gosm_rerun_sensitivity_environmental_conditions.py tests/test_gosm_rerun_sensitivity_p_soil_min.py`
2. optionally run the slow `imag` branch with `GOSM_RUN_SLOW=1`
3. keep repo-wide `pytest` and `ruff` green
