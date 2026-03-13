# Module Spec: Slice 101 THORP Python Rerun Parity

## Goal

Validate the migrated root `THORP` runtime by rerunning the current Python simulation and comparing it directly against the legacy MATLAB `THORP_data_0.6RH.mat` output.

## Source

- `THORP/tests/test_regression_0_6rh.py`
- `THORP/example/THORP_code_forcing_outputs_plotting/Simulations_and_additional_code_to_plot/THORP_data_0.6RH.mat`
- migrated `src/stomatal_optimiaztion/domains/thorp/simulation.py`

## Target

- `tests/test_thorp_rerun_parity.py`

## Requirements

1. run the current root `THORP` Python runtime for the first two simulated weeks (`max_steps=60`)
2. compare the emitted time axis and the first three stored points against the real legacy MATLAB `.mat` payload
3. lock the comparison on the legacy MAT field names so the rerun harness remains aligned with the existing compatibility surface

## Non-Goals

- full-horizon THORP reruns
- reproducing the legacy MATLAB figures
- introducing a new repo-level THORP rerun CLI

## Validation

1. `python -m pytest tests/test_thorp_rerun_parity.py`
2. keep repo-wide `pytest` and `ruff` green
