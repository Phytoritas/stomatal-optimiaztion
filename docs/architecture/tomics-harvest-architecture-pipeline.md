# TOMICS Harvest Architecture Pipeline

## Purpose

Issue `#243` / module `119` promotes harvest from a validation-side aggregation helper into a first-class TOMICS architecture block. Issues `#247`, `#249`, and `#251` then close the zero-yield replay seam, clean harvested-vs-total observation semantics, and rerun the KNU harvest-aware factorial plus promotion gate on the repaired path.

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
  - age-class maturity harvest is implemented, but the committed harvest outflow remains a source-grounded proxy adapter rather than a native TOMGRO runtime
- `dekoning_fds`
  - high-priority research family
  - fruit harvest uses fruit development stage (`FDS`) readiness
  - leaf harvest uses vegetative-unit / corresponding truss colour logic
  - current runtime remains a source-grounded proxy adapter around the traced De Koning readiness and FDMC subrules
- `vanthoor_boxcar`
  - high-priority research family
  - appendix-traced last-stage outflow and `MCLeafHar` semantics are mapped through a source-grounded proxy adapter
  - native fixed-boxcar runtime remains deferred

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

Current runner and validation entrypoints:

- `scripts/run_tomics_knu_harvest_family_factorial.py`
- `scripts/run_tomics_knu_harvest_promotion_gate.py`
- `src/stomatal_optimiaztion/domains/tomato/tomics/alloc/validation/harvest_family_eval.py`
- `src/stomatal_optimiaztion/domains/tomato/tomics/alloc/validation/harvest_family_summary.py`
- `src/stomatal_optimiaztion/domains/tomato/tomics/alloc/validation/harvest_mass_balance_eval.py`
- `src/stomatal_optimiaztion/domains/tomato/tomics/alloc/validation/harvest_calibration_bridge.py`

Current research-family shortlist:

- `vanthoor_boxcar + max_lai_pruning_flow + constant_observed_mean`
- `tomgro_ageclass + vegetative_unit_pruning + constant_observed_mean`

Current selected research harvest family:

- `vanthoor_boxcar + max_lai_pruning_flow + constant_observed_mean`

Promotion-gate result:

- shipped TOMICS plus incumbent TOMSIM harvest remains the incumbent baseline
- no harvest-aware research candidate clears promotion guardrails yet
- the zero-yield replay seam is closed, `any_all_zero_harvest_series = false`, and `post_writeback_dropped_nonharvested_mass_g_m2 = 0` for the promoted-gate comparison bundle
