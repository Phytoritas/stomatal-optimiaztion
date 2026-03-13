## Why
- `slice 085` restored the stomatal-model comparison layer, so the next bounded root `GOSM` gap is the fixed-eta/fixed-NSC operating-point helper in `GOSM/src/gosm/model/instantaneous.py`.
- This seam is the immediate downstream consumer of the migrated runtime pipeline and should land before the broader `steady_state.py` helper.
- The slice should stay bounded to the instantaneous optimum helper, its dataclass output contract, and regression coverage without widening into example scripts.

## Affected model
- `gosm`
- `src/stomatal_optimiaztion/domains/gosm/model/`
- `tests/`
- architecture status docs

## Validation method
- `poetry run pytest`
- `poetry run ruff check .`
- add coverage for equation tagging, interpolation behavior, and representative branch handling

## Comparison target
- legacy `GOSM/src/gosm/model/instantaneous.py`
- current migrated `src/stomatal_optimiaztion/domains/gosm/model/pipeline.py`
- current migrated `src/stomatal_optimiaztion/domains/gosm/params/defaults.py`
