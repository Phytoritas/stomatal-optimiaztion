# Module Spec 094: GOSM Steady-State Inversion Helper

## Purpose

Restore the last missing core root `GOSM` helper from the original MATLAB source: `FUNCTION_Solve_mult_phi_given_assumed_NSC.m`.

## Source Inputs

- `GOSM/example/FUNCTION_Solve_mult_phi_given_assumed_NSC.m`
- migrated `domains/gosm/model/steady_state.py`
- migrated `domains/gosm/model/pipeline.py`

## Target Outputs

- `src/stomatal_optimiaztion/domains/gosm/model/steady_state.py`
- `tests/test_gosm_steady_state_inversion.py`

## Responsibilities

1. preserve the MATLAB-style logspace search over the extensibility multiplier `mult_phi`
2. preserve the temperature-scaled maintenance-respiration rescaling logic for a fixed assumed NSC state
3. keep the seam bounded to steady-state inversion logic without widening into the plotting/example scripts

## Non-Goals

- migrate `Growth_Opt_Stomata.m`
- migrate `Growth_Opt_Stomata_plot_example.m`
- migrate manuscript plotting scripts under `GOSM/example/`

## Validation

- `poetry run pytest`
- `poetry run ruff check .`

## Next Seam

- `TDGM/example/Supplementary Code __THORP_code_v1.4/FUNCTION_Initial_Mean_Allocation_Fractions.m`
