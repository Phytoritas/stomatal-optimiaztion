## Why
- The MATLAB parity audit showed that root `GOSM` still lacks one core helper from the original source: `FUNCTION_Solve_mult_phi_given_assumed_NSC.m`.
- This helper is part of the steady-state inversion workflow, not a figure-only script, so the staged repo is still architecturally incomplete without it.
- The slice should stay bounded to the inversion helper, exports, regression coverage, and architecture-status updates.

## Affected model
- `gosm`
- `src/stomatal_optimiaztion/domains/gosm/model/`
- `tests/`
- architecture status docs

## Validation method
- `poetry run pytest`
- `poetry run ruff check .`
- add MATLAB-style regression coverage over the `E_vect = 0:1e-5:1e-2` search grid that the original helper expects

## Comparison target
- original `GOSM/example/FUNCTION_Solve_mult_phi_given_assumed_NSC.m`
- current migrated `domains/gosm/model/steady_state.py`
- current migrated `domains/gosm/model/pipeline.py`
