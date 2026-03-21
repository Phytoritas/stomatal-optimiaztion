# TOMICS Harvest Architecture Pipeline

## Purpose

Issue `#243` / module `119` promotes harvest from a validation-side aggregation helper into a first-class TOMICS architecture block.

The harvest layer is now separated into four contracts:

- allocator family
- fruit harvest family
- leaf harvest family
- observation / calibration / promotion-gate bridge

## Canonical scaffold

Kuijpers `2019` remains the common structure and interface contract:

- `p`: photosynthesis
- `gr`: growth respiration
- `m`: maintenance respiration
- `xA`: assimilate buffer
- `g`: assimilate partitioning / organ growth
- `xS`: biomass states
- `h1`: fruit harvest
- `h2`: leaf harvest

Harvest families map into `h1` and `h2`; Kuijpers itself is not treated as a standalone harvest biology family.

## Implemented harvest families

### Incumbent baseline

- fruit: `tomsim_truss`
- leaf: `linked_truss_stage`
- semantics: legacy TOMSIM-like truss harvest remains the public baseline comparator

### Research families

- `tomgro_ageclass`
  - research comparator
  - age-class maturity harvest is implemented, but the exact published harvest outflow remains partly proxy-labelled
- `dekoning_fds`
  - high-priority research family
  - fruit harvest uses fruit development stage (`FDS`) readiness
  - leaf harvest uses vegetative-unit / corresponding truss colour logic
- `vanthoor_boxcar`
  - high-priority research family
  - fixed boxcar fruit train with explicit last-stage outflow semantics
  - explicit `MCLeafHar`-style pruning path via max-LAI pruning flow

## Pipeline stages

### HF0

- replay the current public KNU fair-validation baseline unchanged
- verify the public shipped/current/promoted allocator comparison still runs

### HF1

- hold allocator fixed to shipped TOMICS
- compare `tomsim_truss`, `tomgro_ageclass`, `dekoning_fds`, and `vanthoor_boxcar`

### HF2

- cross harvest-family shortlist with:
  - shipped TOMICS
  - current selected allocator `kuijpers_hybrid_candidate`
  - promoted selected allocator `constrained_full_plus_feedback__buffer_capacity_g_m2_12p0`

### HF3

- run family-specific harvest parameter screening on the shortlisted research family

### HF4

- enforce harvest-aware calibration parity
- keep hidden-state and shared parameter freedom explicitly accounted for

### HF5

- rerun the promotion gate with harvest-aware parity

## Current KNU outcome

Current output roots:

- `out/tomics_knu_harvest_family_factorial/`
- `out/tomics_knu_harvest_promotion_gate/`

Current research-family shortlist:

- `vanthoor_boxcar + max_lai_pruning_flow + constant_observed_mean`
- `tomgro_ageclass + vegetative_unit_pruning + constant_observed_mean`

Current selected research harvest family:

- `vanthoor_boxcar + max_lai_pruning_flow + constant_observed_mean`

Promotion-gate result:

- shipped TOMICS plus incumbent TOMSIM harvest remains the incumbent baseline
- no harvest-aware research candidate clears promotion guardrails yet
