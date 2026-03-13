## Why
- The MATLAB parity audit showed one remaining root `TDGM` helper gap: `FUNCTION_Initial_Mean_Allocation_Fractions.m`.
- This helper is small, but it is part of the supplementary THORP-G allocation-memory path and should be present if the staged repo is to match the original MATLAB source cleanly.
- The slice should stay bounded to the initialization helper, exports, regression coverage, and architecture-status updates.

## Affected model
- `tdgm`
- `src/stomatal_optimiaztion/domains/tdgm/`
- `tests/`
- architecture status docs

## Validation method
- `poetry run pytest`
- `poetry run ruff check .`
- add coverage for biomass-proportional horizontal/vertical root partitioning and unity-sum initialization

## Comparison target
- original `TDGM/example/Supplementary Code __THORP_code_v1.4/FUNCTION_Initial_Mean_Allocation_Fractions.m`
- current migrated `domains/tdgm/coupling.py`
