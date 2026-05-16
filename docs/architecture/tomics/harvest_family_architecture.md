# TOMICS Harvest-Family Architecture

The shipped TOMICS incumbent remains unchanged.

For the 2025-2C TOMICS-HAF analysis, fruit DMC is fixed at `0.056`. This is an analysis-layer decision for the 2025-2C observer and later harvest-family evaluation inputs; it does not silently change generic TOMICS or public-dataset defaults.

Dry yield derived from fresh yield using DMC `0.056` is an estimated dry-yield basis, not direct destructive dry-mass measurement unless separately verified.

DMC sensitivity is disabled for the current 2025-2C run unless explicitly re-enabled in a later goal.

Any prior `0.065` DMC references are deprecated previous-default notes for the 2025-2C HAF analysis and must not drive current 2025-2C ranking, scoring, promotion, or paper-primary metrics.

Harvest-family ranking, observation operators, and promotion gate must use DMC `0.056` for 2025-2C.

## HAF 2025-2C wrapper

The HAF 2025-2C harvest-family wrapper consumes:

- the production observer feature frame;
- the production observer metadata;
- latent allocation posteriors and latent metadata.

It emits harvest-family design, manifest, by-loadcell metrics, pooled metrics,
mean-SD metrics, budget parity, mass-balance diagnostics, ranking, selected
research-candidate metadata, and promotion prerequisite summaries under
`out/tomics/validation/harvest-family/haf_2025_2c/`.

Goal 3B output filename contract:

- `harvest_family_factorial_design.csv`
- `harvest_family_run_manifest.csv`
- `harvest_family_metrics_pooled.csv`
- `harvest_family_metrics_by_loadcell.csv`
- `harvest_family_metrics_mean_sd.csv`
- `harvest_family_daily_overlay.csv`
- `harvest_family_cumulative_overlay.csv`
- `harvest_family_mass_balance.csv`
- `harvest_family_budget_parity.csv`
- `harvest_family_rankings.csv`
- `harvest_family_selected_research_candidate.json`
- `harvest_family_prerequisite_promotion_summary.csv`
- `harvest_family_prerequisite_promotion_summary.md`
- `harvest_family_metadata.json`
- `observation_operator_dmc_0p056_audit.csv`
- `no_stale_dmc_0p065_primary_audit.csv`

This wrapper is intentionally separate from the KNU `prepare_knu_bundle()` path
because the KNU path depends on legacy forcing and hidden-state reconstruction
artifacts. The HAF wrapper keeps the same artifact intent while preserving the
2025-2C observer provenance and DMC `0.056` observation contract.

The final promotion gate remains a separate Goal 3C action.
