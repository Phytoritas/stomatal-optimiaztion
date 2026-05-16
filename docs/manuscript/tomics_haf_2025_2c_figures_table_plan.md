# TOMICS-HAF 2025-2C Figures And Table Plan

| group | planned item | evidence path | readiness |
| --- | --- | --- | --- |
| Observer | Radiation-defined day/night ET summary | `out/tomics/analysis/haf_2025_2c/radiation_daynight_event_bridged_daily_main_0W.csv` | data ready, figure pending |
| Observer | Root-zone RZI and apparent conductance summary | `out/tomics/analysis/haf_2025_2c/2025_2c_rootzone_indices.csv` | data ready, figure pending |
| Latent allocation | Prior/posterior and guardrail diagnostics | `out/tomics/validation/latent-allocation/haf_2025_2c/` | data ready, figure pending |
| Harvest-family | Candidate ranking and by-loadcell metrics | `out/tomics/validation/harvest-family/haf_2025_2c/harvest_family_rankings.csv` | data ready, figure pending |
| Promotion gate | Gate scorecard and blockers | `out/tomics/validation/promotion-gate/haf_2025_2c/promotion_gate_scorecard.csv` | table ready |
| Cross-dataset gate | Dataset count and blockers | `out/tomics/validation/multi-dataset/haf_2025_2c/cross_dataset_metadata.json` | table ready |
| Claim safety | Claim register and boundary freeze | `out/tomics/validation/promotion-gate/haf_2025_2c/claim_register.md` | table ready |
| Readiness | New Phytologist readiness matrix | `out/tomics/validation/promotion-gate/haf_2025_2c/new_phytologist_readiness_matrix.md` | table ready, final readiness blocked |

Plotkit manifest:

```text
out/tomics/figures/haf_2025_2c/plotkit_render_manifest.*
```

Rendered PNGs are pending renderer work. Do not claim a completed rendered figure bundle while the manifest reports zero rendered PNGs.
