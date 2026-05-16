# TOMICS-HAF 2025-2C Actual Data Observer Pipeline

Goal 1 schema and radiation verification passed for the required 2025-2C raw inputs. Dataset1 `env_inside_radiation_wm2` is directly usable for radiation-defined day/night. The raw `.dat` `SolarRad_Avg` signal is fallback-only and is not required as the primary day/night source for this observer run.

Goal 2 builds a thin TOMICS-HAF observer/profile layer. It produces:

- radiation-defined 10-minute day/night intervals for thresholds `0`, `1`, `5`, and `10 W m-2`;
- photoperiod tables;
- event-bridged water-flux interval and daily summaries;
- fruit/leaf QC and radiation-window observer summaries;
- fixed `06:00-18:00` compatibility-only summaries;
- Dataset2 root-zone moisture/EC/tensiometer indices;
- apparent canopy conductance when VPD is available;
- Dataset3 growth/phenology bridge outputs;
- the TOMICS-HAF observer feature frame.

Goal 1 established that VPD is available. LAI is unavailable and is not fabricated. Fresh/dry yield aliases are unavailable under the verified alias contract unless a later source is separately verified.

Dataset3 is direct-loadcell mappable, but date/datetime and truss-position alias limitations remain. Without a safe date key, Dataset3 is emitted as direct-loadcell standalone structural/phenology summaries rather than causal allocation fitting data.

The observer feature frame is a prerequisite scaffold for later latent allocation inference and harvest-family evaluation. Latent allocation inference, harvest-family factorial evaluation, cross-dataset gates, and promotion gates are not run in Goal 2.

Shipped TOMICS incumbent behavior remains unchanged.

Goal 2.5 hardens the observer export for production by adding chunk aggregation for full Dataset1 and Dataset2 processing. Smoke mode remains capped for fast local checks, while production mode is expected to process all projected parquet rows without full in-memory materialization. The production observer feature frame is a prerequisite input scaffold for later latent allocation inference; it does not infer allocation.

Goal 3A.6 fixes fruit DMC at `0.056` for the 2025-2C TOMICS-HAF analysis. Dry yield derived from fresh yield using DMC `0.056` is an estimated dry-yield basis, not direct destructive dry-mass measurement unless separately verified. DMC sensitivity is disabled for the current 2025-2C run unless explicitly re-enabled in a later goal. Any prior `0.065` DMC references are deprecated previous-default notes and must not drive 2025-2C metrics. Harvest-family ranking, observation operators, and promotion gate must use DMC `0.056` for 2025-2C.
