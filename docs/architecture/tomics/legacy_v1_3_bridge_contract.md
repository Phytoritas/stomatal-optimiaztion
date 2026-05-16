# Legacy v1.3 Bridge Contract

Goal 3A.5 may read selected TOMICS v1.3 derived outputs as provenance-tagged bridge inputs for observer hardening. These files are legacy derived outputs, not raw observations.

Allowed bridge surfaces:

- `previous_outputs/event_bridge_outputs/daily_event_bridged_transpiration.csv`
- `outputs/derived/legacy_daily_event_bridged_transpiration.csv`
- `outputs/derived/integrated_daily_master_radiation_daynight_fresh_dry.csv`
- `outputs/tables/fresh_dry_weight_loadcell_final_summary.csv`
- `outputs/tables/fresh_dry_weight_treatment_summary.csv`
- `outputs/derived/dataset3_traits_plus_fresh_dry_yield.csv`

Every imported value must keep `legacy_v1_3_derived_output` provenance. The bridge may calibrate current production event-bridged ET only when date, loadcell, treatment, finite daily total, coverage, and QC checks pass.

For the 2025-2C TOMICS-HAF analysis, fruit DMC is fixed at `0.056`. Legacy v1.3 fresh/dry yield outputs are provenance-tagged derived outputs, not raw observations. Dry yield derived from fresh yield using DMC `0.056` is an estimated dry-yield basis, not direct destructive dry-mass measurement unless separately verified.

DMC sensitivity is disabled for the current 2025-2C run unless explicitly re-enabled in a later goal. Prior `0.065` DMC references are deprecated previous-default notes only.

The bridge must not change shipped TOMICS defaults, promote any allocator, or convert latent allocation inference into direct validation.
