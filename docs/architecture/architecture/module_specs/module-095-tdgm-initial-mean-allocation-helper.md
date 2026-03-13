# Module Spec 095: TDGM Initial Mean-Allocation Helper

## Purpose

Restore the last missing bounded helper found by the MATLAB parity audit: `FUNCTION_Initial_Mean_Allocation_Fractions.m` from the supplementary THORP-G path.

## Source Inputs

- `TDGM/example/Supplementary Code __THORP_code_v1.4/FUNCTION_Initial_Mean_Allocation_Fractions.m`
- migrated `domains/tdgm/coupling.py`

## Target Outputs

- `src/stomatal_optimiaztion/domains/tdgm/coupling.py`
- `tests/test_tdgm_coupling.py`

## Responsibilities

1. preserve the fixed `0.3 / 0.3 / 0.4` stem-leaf-root split
2. preserve the biomass-proportional distribution of horizontal and vertical root allocation fractions
3. keep the seam bounded to allocation-memory initialization without widening into analysis or plotting scripts

## Non-Goals

- migrate `ANALYSIS_*.m`
- migrate `PLOT_*.m`
- widen the seam into a full supplementary THORP-G runner

## Validation

- `poetry run pytest`
- `poetry run ruff check .`

## Next Seam

- none; close the current MATLAB parity audit wave
