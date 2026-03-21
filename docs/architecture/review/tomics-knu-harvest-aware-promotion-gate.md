# TOMICS KNU Harvest-aware Promotion Gate

## Purpose

Issue `#243` / module `119` reruns the KNU promotion gate after separating allocator family and harvest family.

The gate compares:

- shipped TOMICS + incumbent TOMSIM harvest
- current selected allocator + selected research harvest family
- promoted selected allocator + selected research harvest family

## Current selected research harvest family

- fruit harvest family: `vanthoor_boxcar`
- leaf harvest family: `max_lai_pruning_flow`
- `fdmc_mode`: `constant_observed_mean`

## Current scorecard

Output roots:

- `out/tomics_knu_harvest_family_factorial/`
- `out/tomics_knu_harvest_promotion_gate/`

Current mean holdout results:

- shipped TOMICS + incumbent TOMSIM harvest
  - RMSE cumulative offset: `33.3229`
  - RMSE daily increment: `4.9743`
  - canopy collapse days: `22`
- current selected + selected research harvest family
  - RMSE cumulative offset: `33.3229`
  - RMSE daily increment: `4.9743`
  - fruit-anchor error vs legacy: `0.0112`
  - canopy collapse days: `11`
- promoted selected + selected research harvest family
  - RMSE cumulative offset: `33.3229`
  - RMSE daily increment: `4.9743`
  - fruit-anchor error vs legacy: `0.0112`
  - canopy collapse days: `11`

## Gate decision

Recommendation:

- `Keep shipped TOMICS + incumbent TOMSIM harvest as the incumbent baseline.`

Reason:

- no research candidate produces a material holdout improvement over shipped baseline
- research candidates still fail the canopy-collapse guardrail
- harvest mass balance is clean, but that is not enough on its own to justify promotion

## Interpretation

The current best research harvest family helps organize the architecture cleanly and is useful for further research-only screening, but it does not yet provide a promotion-grade validation win on KNU actual data.
