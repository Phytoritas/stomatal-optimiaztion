# Module 117: TOMICS Current vs Promoted Factorial on KNU Data

## Problem

The previous TOMICS allocation architecture pipeline selected research candidates only on synthetic/proxy forcing.

That was enough for architecture screening, but not enough for a promotion decision.

The next step must validate both:

- the current merged research family
- the promoted constrained-marginal allocator family

against actual KNU greenhouse forcing and measured cumulative fruit dry weight.

## Inputs

- `data/forcing/KNU_Tomato_Env.CSV`
- `data/forcing/tomato_validation_data_yield_260222.xlsx`
- current research architecture config from `configs/exp/tomics_allocation_factorial.yaml`
- current shipped `tomics` and legacy / raw THORP-like policy paths

## New seams

- `src/stomatal_optimiaztion/domains/tomato/tomics/alloc/validation/knu_data.py`
- `src/stomatal_optimiaztion/domains/tomato/tomics/alloc/validation/theta_proxy.py`
- `src/stomatal_optimiaztion/domains/tomato/tomics/alloc/validation/metrics.py`
- `src/stomatal_optimiaztion/domains/tomato/tomics/alloc/validation/current_vs_promoted.py`
- `scripts/prepare_knu_longrun_validation.py`
- `scripts/run_tomics_current_vs_promoted_factorial.py`

## Contracts

### Validation boundary

- all final validation metrics are on floor-area basis
- observed workbook units are preserved exactly as declared
- offset-adjusted cumulative metrics are reported and preferred when the observed series starts above zero

### Theta proxy

- default actual-data proxy mode: `bucket_irrigated`
- greenhouse bounds: `0.40` to `0.85`
- scenarios: `dry`, `moderate`, `wet`

### Study outputs

Current study root:

- `out/tomics_current_factorial_knu/`

Promoted study root:

- `out/tomics_promoted_factorial_knu/`

Comparison root:

- `out/tomics_current_vs_promoted_knu/`

## Guardrails

- shipped `partition_policy: tomics` semantics must not change
- old tomato runtime imports must not return
- THORP must remain a bounded root-correction source only
- the promoted allocator must not be promoted if it loses the fruit anchor, collapses canopy behavior, or only wins by short-window overfit

## Current decision

Module `117` keeps the promoted allocator research-only.
