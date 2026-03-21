# TOMICS KNU Harvest-aware Promotion Gate

## Purpose

Issue `#243` / module `119` adds the harvest-aware promotion gate. Issues `#247` and `#249` then repair the external-harvest zero-yield seam and clean harvested-vs-total observation semantics, and issue `#251` reruns the KNU harvest-aware factorial plus promotion gate on that repaired path.

The gate compares:

- shipped TOMICS + incumbent TOMSIM harvest
- current selected allocator + selected research harvest family
- promoted selected allocator + selected research harvest family

Primary runner and validation entrypoints:

- `scripts/run_tomics_knu_harvest_family_factorial.py`
- `scripts/run_tomics_knu_harvest_promotion_gate.py`
- `src/stomatal_optimiaztion/domains/tomato/tomics/alloc/validation/harvest_family_eval.py`
- `src/stomatal_optimiaztion/domains/tomato/tomics/alloc/validation/harvest_family_summary.py`
- `src/stomatal_optimiaztion/domains/tomato/tomics/alloc/validation/harvest_mass_balance_eval.py`
- `src/stomatal_optimiaztion/domains/tomato/tomics/alloc/validation/harvest_calibration_bridge.py`

## Current selected research harvest family

- fruit harvest family: `vanthoor_boxcar`
- leaf harvest family: `max_lai_pruning_flow`
- `fdmc_mode`: `constant_observed_mean`
- status: research-only source-grounded proxy adapter; this is not a claim that a native Vanthoor fixed-boxcar runtime is already public

## Current scorecard

Output roots:

- `out/tomics_knu_harvest_family_factorial/`
- `out/tomics_knu_harvest_promotion_gate/`

Current mean holdout results:

- shipped TOMICS + incumbent TOMSIM harvest
  - RMSE cumulative offset: `33.3229`
  - RMSE daily increment: `4.9743`
  - canopy collapse days: `47`
  - post-writeback dropped nonharvested mass: `0.0`
  - any all-zero harvest series: `false`
- current selected + selected research harvest family
  - RMSE cumulative offset: `33.3086`
  - RMSE daily increment: `4.9730`
  - fruit-anchor error vs legacy: `0.0112`
  - canopy collapse days: `11`
  - post-writeback dropped nonharvested mass: `0.0`
  - any all-zero harvest series: `false`
  - winner stability score: `0.00`
- promoted selected + selected research harvest family
  - RMSE cumulative offset: `33.3086`
  - RMSE daily increment: `4.9730`
  - fruit-anchor error vs legacy: `0.0112`
  - canopy collapse days: `11`
  - post-writeback dropped nonharvested mass: `0.0`
  - any all-zero harvest series: `false`
  - winner stability score: `0.00`

The repaired harvest replay now reaches the public score surface cleanly:

- `post_writeback_dropped_nonharvested_mass_g_m2 = 0`
- `any_all_zero_harvest_series = false`

## Gate decision

Recommendation:

- `Keep shipped TOMICS + incumbent TOMSIM harvest as the incumbent baseline.`

Reason:

- the best research candidates improve cumulative RMSE by only about `0.0144`, far below the material improvement margin `0.5`
- the best research candidates improve daily RMSE by only about `0.0013`, far below the material improvement margin `0.25`
- current selected and promoted selected still fail the canopy-collapse guardrail
- current selected and promoted selected still fail the winner-stability guardrail
- harvest mass balance and post-writeback audit are clean, but clean accounting alone does not justify promotion

## Interpretation

The current best research harvest family helps organize the architecture cleanly and remains useful for research-only screening, but it still does not provide a promotion-grade validation win on KNU actual data. The incumbent public baseline therefore remains the shipped TOMICS allocator with incumbent TOMSIM harvest semantics.
