## Why
- `slice 086` restored the instantaneous optimum helper, so the next bounded root `GOSM` gap is the steady-state NSC/CUE helper in `GOSM/src/gosm/model/steady_state.py`.
- This seam closes the remaining major legacy control-analysis path before the refactoring wave moves on to root `TDGM` runtime seams.
- The slice should stay bounded to the steady-state helper, its vectorized Newton/quadratic branches, and regression coverage without widening into example scripts.

## Affected model
- `gosm`
- `src/stomatal_optimiaztion/domains/gosm/model/`
- `tests/`
- architecture status docs

## Validation method
- `poetry run pytest`
- `poetry run ruff check .`
- add coverage for equation tagging, representative steady-state outputs, and branch-specific helper behavior

## Comparison target
- legacy `GOSM/src/gosm/model/steady_state.py`
- current migrated `src/stomatal_optimiaztion/domains/gosm/model/pipeline.py`
- current migrated `src/stomatal_optimiaztion/domains/gosm/model/instantaneous.py`
