# TOMICS-HAF 2025-2C Production Observer Export

Goal 2 smoke validation succeeded, but it used bounded row caps for private local runtime safety: Dataset1 was capped at `1,000,000 / 139,713,462` rows and Dataset2 was capped at `500,000 / 46,571,154` rows.

Goal 2.5 adds production chunk aggregation so downstream latent allocation does not run on row-capped observer data. Production mode reads projected parquet batches and aggregates Dataset1 directly to 10-minute loadcell/treatment intervals, while aggregating Dataset2 to daily loadcell/treatment root-zone summaries. Production mode must not concatenate full Dataset1 or Dataset2 into memory.

Dataset1 still defines day/night phases with `env_inside_radiation_wm2`. The main threshold is `0 W m-2`, and sensitivity thresholds remain `0`, `1`, `5`, and `10 W m-2`. Fixed `06:00-18:00` windows remain compatibility-only. raw `.dat` `SolarRad_Avg` remains fallback-only for this 2025-2C dataset.

Fruit diameter remains sensor-level apparent expansion diagnostics only. It is not a treatment endpoint, p-value source, allocation calibration target, hydraulic gate calibration target, or model-promotion target.

Full production observer export is a prerequisite for latent allocation inference on actual 2025-2C data. Latent allocation inference, harvest-family factorials, cross-dataset gates, and promotion gates remain blocked until production observer export completes and metadata reports `production_ready_for_latent_allocation = true`.

The production metadata contract records total rows, processed rows, processed fractions, batch counts, row-cap status, chunk aggregation status, water-flux carryover status, and whether full in-memory loading was avoided.

