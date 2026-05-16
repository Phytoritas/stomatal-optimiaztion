# PR 309 Goal 2.5 Summary

Suggested PR title:

`[TOMICS] Add HAF 2025-2C observer pipeline`

## Summary

Closes #308

- Preserves the original #308 daily-harvest diagnostic commit.
- Adds the TOMICS-HAF 2025-2C observer pipeline.
- Adds production-ready chunk aggregation for full Dataset1/Dataset2 observer export.
- Keeps Dataset1 `env_inside_radiation_wm2` radiation-defined day/night as primary.
- Keeps fixed `06:00-18:00` windows compatibility-only.
- Keeps raw `.dat` `SolarRad_Avg` fallback-only for 2025-2C.
- Keeps fruit diameter sensor-level apparent expansion diagnostics only.
- Keeps shipped TOMICS incumbent unchanged.
- Does not run latent allocation, harvest-family factorial, cross-dataset gate, or promotion gate.

## Validation

- Targeted Goal 2.5 + Goal 2 observer tests: `16 passed`.
- Ruff: `All checks passed`.
- Full pytest: `600 passed, 26 skipped, 12 deselected`.
- Smoke observer run: succeeded with row caps and `production_ready_for_latent_allocation = false`.
- Production observer run: succeeded with Dataset1 `139,713,462 / 139,713,462` rows and Dataset2 `46,571,154 / 46,571,154` rows processed.

## Production Export

- `observer_pipeline_mode = production`.
- `chunk_aggregation_used = true`.
- `full_in_memory_large_dataset_used = false`.
- `row_cap_applied = false`.
- `production_export_completed = true`.
- `production_ready_for_latent_allocation = true`.

## Unresolved Assumptions

- Fruit1/Fruit2 mapping remains provisional.
- Dataset3 remains `direct_loadcell_no_date` unless verified otherwise.
- Event-bridged ET remains uncalibrated where existing daily totals are unavailable.
- LAI and harvest yield remain unavailable unless separately verified.
- Latent allocation inference is blocked until a later explicit goal.

## Safe Interpretation

Goal 2.5 makes the observer feature frame production-ready for later latent allocation; it does not infer allocation.

Day/night phases remain radiation-defined from Dataset1 `env_inside_radiation_wm2`, not fixed `06:00-18:00`.

Fruit diameter remains sensor-level apparent expansion diagnostics.

Shipped TOMICS incumbent remains unchanged.
