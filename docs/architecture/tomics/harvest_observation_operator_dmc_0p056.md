# HAF 2025-2C Harvest Observation Operator DMC 0.056

For 2025-2C, DMC is fixed at `0.056`.

The observation operator family is `fresh_to_dry_dmc_0p056`:

```text
observed_fruit_DW_g_loadcell = observed_fruit_FW_g_loadcell * 0.056
observed_fruit_DW_g_m2_floor = observed_fruit_FW_g_loadcell * 0.056 / 3.148672656
model_fruit_FW_g_loadcell = model_fruit_DW_g_m2_floor * 3.148672656 / 0.056
```

Dry yield derived from fresh yield using DMC `0.056` is an estimated
dry-yield basis, not direct destructive dry-mass measurement unless separately
verified.

The Goal 3B runner writes `observation_operator_dmc_0p056_audit.csv` and
`no_stale_dmc_0p065_primary_audit.csv`. `constant_0p065` and `dmc_sensitivity`
are forbidden primary modes for the current 2025-2C run.
