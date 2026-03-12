## Background
- `slice 031` landed the TOMATO partitioning core, but every THORP-derived tomato policy alias was still blocked behind `NotImplementedError`.
- This PR lands `slice 032` by migrating the THORP-backed tomato allocation adapter and policy layer, and moves the next TOMATO seam to the package-level legacy pipeline wrapper.

## Changes
- add TOMATO partitioning adapters for `ThorpObjectiveParams`, THORP allocation fractions, and collapsed tomato partition outputs
- add `ThorpVegetativePolicy` and `ThorpFruitVegPolicy`, then wire `build_partition_policy()` aliases to real policy instances
- expand partitioning tests to cover wrapper behavior, THORP-policy invariants, and `TomatoModel(partition_policy=\"thorp_veg\")`
- update architecture artifacts to record `slice 032`

## Validation
- `.venv\Scripts\python.exe -m pytest`
- `.venv\Scripts\ruff.exe check .`

## Impact
- TOMATO partition-policy aliases now resolve to concrete migrated policies instead of runtime blockers
- the next bounded TOMATO seam shifts from partitioning internals to `pipelines/tomato_legacy.py`

## Linked issue
Closes #57
