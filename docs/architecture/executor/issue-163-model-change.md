## Why
- `slice 083` restored the first fully wired root `GOSM` runtime path, so the next bounded seam is the small paper-alternative helper layer in `GOSM/src/gosm/model/future_work.py`.
- This seam is independent of the remaining `stomata_models`, `instantaneous`, and `steady_state` layers, so it is the safest next slice before opening broader control helpers.
- The slice should stay helper-bounded to equation-tagged future-work formulas plus regression coverage and should not widen into example scripts or policy layers.

## Affected model
- `gosm`
- `src/stomatal_optimiaztion/domains/gosm/model/`
- `tests/`
- architecture status docs

## Validation method
- `poetry run pytest`
- `poetry run ruff check .`
- add coverage for equation tagging, numerical helper behavior, and legacy alias handling

## Comparison target
- legacy `GOSM/src/gosm/model/future_work.py`
- current migrated `src/stomatal_optimiaztion/domains/gosm/model/`
- packaged `gosm` traceability helpers
