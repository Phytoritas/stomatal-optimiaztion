## Background
- `slice 030` landed the TOMATO runner seam, but default tomato allocation still lived as inline fallback logic inside the migrated `TomatoModel`.
- This PR lands `slice 031` by introducing a package-local partitioning core plus the default sink-based tomato policy, and moves the next blocked seam to the THORP-derived partitioning helpers.

## Changes
- add TOMATO partitioning core modules for `Organ`, `AllocationFractions`, `PartitionPolicy`, and `SinkBasedTomatoPolicy`
- wire `TomatoModel` to the migrated sink-based policy via `coerce_partition_policy()`
- add partitioning conversion and invariant tests, and update architecture artifacts to record `slice 031`

## Validation
- `.venv\Scripts\python.exe -m pytest`
- `.venv\Scripts\ruff.exe check .`

## Impact
- default TOMATO partitioning now lives behind an explicit package-local seam instead of inline fallback logic
- THORP-derived partitioning remains explicitly blocked and documented for the next slice

## Linked issue
Closes #55
