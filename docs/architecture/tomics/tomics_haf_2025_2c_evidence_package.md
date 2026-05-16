# TOMICS-HAF 2025-2C Evidence Package

This package indexes the evidence needed for paper and thesis drafting while preserving the Goal 4A claim boundary. Private generated outputs under `out/` are not committed; this document records what they support and what they do not support.

## Observer Evidence

- Production observer metadata: `out/tomics/analysis/haf_2025_2c/2025_2c_tomics_haf_metadata.json`
- Radiation day/night summaries: `out/tomics/analysis/haf_2025_2c/radiation_daynight_event_bridged_daily_main_0W.csv`
- Event-bridged ET outputs: `out/tomics/analysis/haf_2025_2c/radiation_daynight_event_bridged_daily_all_thresholds.csv`
- Root-zone RZI outputs: `out/tomics/analysis/haf_2025_2c/2025_2c_rootzone_indices.csv`
- Fruit/leaf observer outputs: `out/tomics/analysis/haf_2025_2c/2025_2c_fruit_leaf_radiation_windows.csv`
- Dataset3 bridge outputs: `out/tomics/analysis/haf_2025_2c/2025_2c_dataset3_growth_phenology_bridge.csv`
- Observer feature frame: `out/tomics/analysis/haf_2025_2c/2025_2c_tomics_haf_observer_feature_frame.csv`

Supported claim boundary: day/night phases were radiation-defined from Dataset1 `env_inside_radiation_wm2`. Fruit diameter remains diagnostic only.

## Latent Allocation Evidence

- Input state: `out/tomics/validation/latent-allocation/haf_2025_2c/latent_allocation_inference_inputs.csv`
- Priors: `out/tomics/validation/latent-allocation/haf_2025_2c/latent_allocation_priors.csv`
- Posteriors: `out/tomics/validation/latent-allocation/haf_2025_2c/latent_allocation_posteriors.csv`
- Diagnostics: `out/tomics/validation/latent-allocation/haf_2025_2c/latent_allocation_diagnostics.csv`
- Identifiability: `out/tomics/validation/latent-allocation/haf_2025_2c/latent_allocation_identifiability.csv`
- Guardrails: `out/tomics/validation/latent-allocation/haf_2025_2c/latent_allocation_guardrails.csv`
- Metadata: `out/tomics/validation/latent-allocation/haf_2025_2c/latent_allocation_metadata.json`

Supported claim boundary: latent allocation is observer-supported inference, not direct allocation validation.

## Harvest-Family Evidence

- Design: `docs/architecture/tomics/harvest_family_factorial_design_2025_2c.md`
- Run manifest: `out/tomics/validation/harvest-family/haf_2025_2c/harvest_family_run_manifest.csv`
- Metrics pooled: `out/tomics/validation/harvest-family/haf_2025_2c/harvest_family_metrics_pooled.csv`
- Metrics by loadcell: `out/tomics/validation/harvest-family/haf_2025_2c/harvest_family_metrics_by_loadcell.csv`
- Metrics mean and SD: `out/tomics/validation/harvest-family/haf_2025_2c/harvest_family_metrics_mean_sd.csv`
- Mass balance: `out/tomics/validation/harvest-family/haf_2025_2c/harvest_family_mass_balance.csv`
- Budget parity: `out/tomics/validation/harvest-family/haf_2025_2c/harvest_family_budget_parity.csv`
- Rankings: `out/tomics/validation/harvest-family/haf_2025_2c/harvest_family_rankings.csv`
- Selected research candidate: `out/tomics/validation/harvest-family/haf_2025_2c/harvest_family_selected_research_candidate.json`
- Reproducibility manifest: `out/tomics/validation/harvest-family/haf_2025_2c/harvest_family_reproducibility_manifest.json`

Supported claim boundary: harvest-family evaluation separated allocator family, harvest family, and observation operator. Candidate selection is for future cross-dataset testing only.

## Promotion And Cross-Dataset Evidence

- Promotion scorecard: `out/tomics/validation/promotion-gate/haf_2025_2c/promotion_gate_scorecard.csv`
- Promotion metadata: `out/tomics/validation/promotion-gate/haf_2025_2c/promotion_gate_metadata.json`
- Promotion blockers: `out/tomics/validation/promotion-gate/haf_2025_2c/promotion_gate_blockers.csv`
- Future candidate: `out/tomics/validation/promotion-gate/haf_2025_2c/promotion_candidate_for_future_gate.json`
- Cross-dataset scorecard: `out/tomics/validation/multi-dataset/haf_2025_2c/cross_dataset_scorecard.csv`
- Cross-dataset metadata: `out/tomics/validation/multi-dataset/haf_2025_2c/cross_dataset_metadata.json`
- Claim register: `out/tomics/validation/promotion-gate/haf_2025_2c/claim_register.md`
- New Phytologist readiness matrix: `out/tomics/validation/promotion-gate/haf_2025_2c/new_phytologist_readiness_matrix.md`

Supported claim boundary: promotion and cross-dataset gates were executed as safeguards. The shipped TOMICS default remains unchanged.

## Figure Evidence

- Plotkit render manifest CSV: `out/tomics/figures/haf_2025_2c/plotkit_render_manifest.csv`
- Plotkit render manifest MD: `out/tomics/figures/haf_2025_2c/plotkit_render_manifest.md`

The current figure state is manifest-backed. Rendered PNG evidence is pending and must not be claimed complete until a renderer produces real PNGs.

Machine-readable package manifest:

```text
out/tomics/validation/promotion-gate/haf_2025_2c/evidence_package_manifest.*
```
