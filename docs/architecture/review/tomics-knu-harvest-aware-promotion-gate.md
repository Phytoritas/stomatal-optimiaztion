# TOMICS KNU Harvest-aware Promotion Gate

## Purpose

Issue `#255` reruns the KNU promotion gate after PR `#254` lands the runtime-complete harvest state/writeback contract on `main`.

The gate compares:

- shipped TOMICS + incumbent TOMSIM harvest
- current selected allocator + selected research harvest family
- promoted selected allocator + selected research harvest family

## Current selected research harvest family

- fruit harvest family: `dekoning_fds`
- leaf harvest family: `vegetative_unit_pruning`
- `fdmc_mode`: `dekoning_fds`

## Current scorecard

Output roots:

- `out/tomics_knu_harvest_family_factorial/`
- `out/tomics_knu_harvest_promotion_gate/`

Current mean holdout results:

- shipped TOMICS + incumbent TOMSIM harvest
  - RMSE cumulative offset: `33.3229`
  - RMSE daily increment: `4.9743`
  - canopy collapse days: `47`
- current selected + selected research harvest family
  - RMSE cumulative offset: `33.3229`
  - RMSE daily increment: `4.9743`
  - canopy collapse days: `11`
  - winner stability score: `1.00`
- promoted selected + selected research harvest family
  - RMSE cumulative offset: `33.3229`
  - RMSE daily increment: `4.9743`
  - canopy collapse days: `11`
  - winner stability score: `0.00`

Current audit flags:

- `any_all_zero_harvest_series = false` for shipped/current/promoted
- `any_offplant_with_positive_mass_flag = false`
- `max_post_writeback_dropped_nonharvested_mass_g_m2 = 0.0`

## Gate decision

Recommendation:

- `Keep shipped TOMICS + incumbent TOMSIM harvest as the incumbent baseline.`

Reason:

- no research candidate produces a material holdout improvement over shipped baseline
- research candidates still fail the canopy-collapse guardrail
- current selected wins all three holdout comparisons, but promoted does not reproduce that stability
- harvest mass balance is clean, but that is not enough on its own to justify promotion

## Interpretation

The current best research harvest family helps organize the architecture cleanly and is useful for further research-only screening, but it does not yet provide a promotion-grade validation win on KNU actual data.

The runtime-complete rerun also narrows the interpretation boundary:

- the selected research family is `dekoning_fds`, not `vanthoor_boxcar`
- `dekoning_fds`, `tomgro_ageclass`, and `vanthoor_boxcar` still remain effectively tied on the current KNU window, so family discrimination is weak
- the sampled KNU lane still records `shared_tdvs_proxy` / `proxy_mode_used = true` for research families, so the winner should not be over-described as a fully native harvest-runtime win
