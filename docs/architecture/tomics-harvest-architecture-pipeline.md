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

## Runtime completion rules

Issue `#253` adds the missing runtime state needed to stop the four harvest families from collapsing onto the same proxy post-maturity surface.

- fruit entities now carry post-maturity lifecycle axes such as `matured_at`, `days_since_maturity`, `mature_pool_residence_days`, and `final_stage_residence_days`
- `harvest_delay_days` is treated as a post-maturity residence gate, not as threshold inflation
- mature or sink-inactive fruit can remain on-plant until a harvest event occurs
- partial fruit outflow leaves residual on-plant fruit mass in place until residual mass is effectively zero
- common-structure `h1` / `h2` are wired to step harvest fluxes, not cumulative harvested pools
- validation scoring reads explicit harvested cumulative output and keeps legacy total-fruit aliases only for compatibility

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

Runtime-complete probe result:

- `matured_at` and `days_since_maturity` populate in the actual KNU lane
- common-structure harvest step flux matches baseline-adjusted harvested cumulative daily diffs
- `offplant_with_positive_mass_flag` stays false and `post_writeback_dropped_nonharvested_mass_g_m2` stays zero
- `partial_outflow_flag` round-trips as a diagnostic field, but the current KNU window does not trigger a partial-outflow event
- `tomsim_truss` reaches both `native_payload` and `shared_tdvs_proxy` states in the sampled window, while `tomgro_ageclass`, `dekoning_fds`, and `vanthoor_boxcar` still report `shared_tdvs_proxy` with `proxy_mode_used = true`

Current research-family shortlist:

- `dekoning_fds + vegetative_unit_pruning + dekoning_fds`
- `tomgro_ageclass + vegetative_unit_pruning + constant_observed_mean`

Current selected research harvest family:

- `dekoning_fds + vegetative_unit_pruning + dekoning_fds`

Promotion-gate result:

- shipped TOMICS plus incumbent TOMSIM harvest remains the incumbent baseline
- no harvest-aware research candidate clears promotion guardrails yet
- shipped, current, and promoted holdout RMSE remain tied at `33.3229` cumulative offset and `4.9743` daily increment on the current KNU window
- the runtime-complete rerun therefore improves contract coverage, not practical family discrimination; the selected research family is still partly proxy-dependent in this window
