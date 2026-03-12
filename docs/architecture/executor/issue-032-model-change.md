## Why
- `slice 031` landed the TOMATO partitioning core, but all THORP-derived tomato policy aliases still raise `NotImplementedError`.
- The next bounded seam is the THORP-backed tomato partition adapter layer that owns `thorp_opt.py`, `thorp_policies.py`, and policy-builder wiring for `thorp_veg` / `thorp_fruit_veg`.

## Affected model
- `TOMATO tTHORP`
- `src/stomatal_optimiaztion/domains/tomato/tthorp/components/partitioning/`
- related TOMATO `TomatoModel` and partition-policy integration tests

## Validation method
- `poetry run pytest`
- `poetry run ruff check .`
- add wrapper-equivalence, THORP-policy alias, and `TomatoModel(partition_policy="thorp_veg")` coverage

## Comparison target
- legacy `TOMATO/tTHORP/src/tthorp/components/partitioning/{thorp_opt.py,thorp_policies.py}`
- current migrated `domains/thorp/allocation.py` core behavior
