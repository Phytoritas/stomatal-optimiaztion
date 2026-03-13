# Module Spec: Slice 105 GOSM Warning-Free Rerun Hardening

## Goal

Eliminate the remaining `RuntimeWarning` emissions from the root `GOSM` rerun path while preserving direct Python-versus-MATLAB parity.

## Source

- root `GOSM` rerun parity slices `102` and `104`
- migrated `gosm` hydraulics and conductance kernels
- fast and slow root `GOSM` rerun parity tests

## Target

- `src/stomatal_optimiaztion/domains/gosm/model/hydraulics.py`
- `src/stomatal_optimiaztion/domains/gosm/model/conductance_temperature.py`
- `src/stomatal_optimiaztion/domains/gosm/model/stomata_models.py`
- `src/stomatal_optimiaztion/domains/gosm/examples/control.py`
- `src/stomatal_optimiaztion/domains/gosm/examples/sensitivity.py`
- `tests/test_gosm_rerun_control.py`
- `tests/test_gosm_rerun_sensitivity_environmental_conditions.py`
- `tests/test_gosm_rerun_sensitivity_p_soil_min.py`
- `docs/architecture/review/python-rerun-parity-audit-note.md`

## Requirements

1. keep root `GOSM` rerun outputs numerically aligned with the legacy MATLAB payloads
2. remove rerun-time `RuntimeWarning` emissions from the fast control and sensitivity paths
3. keep the slow `imag` conductance-loss branch warning-free when explicitly enabled
4. enforce warning-free reruns in regression tests via `warnings-as-errors`

## Non-Goals

- changing the underlying `GOSM` equations
- broad runtime optimization outside the rerun path
- reopening the closed root `THORP` or `TDGM` rerun waves

## Validation

1. `GOSM` fast rerun parity tests must pass under `-W error::RuntimeWarning`
2. the opt-in slow `imag` rerun branch must pass under `-W error::RuntimeWarning`
3. repo-wide `pytest` and `ruff` must pass
