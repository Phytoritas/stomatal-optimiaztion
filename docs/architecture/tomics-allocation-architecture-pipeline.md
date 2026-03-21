# TOMICS Allocation Architecture Pipeline

## Purpose

This architecture pipeline extends the live TOMICS-Alloc surface without changing the shipped default behavior of `partition_policy: tomics`.

The current shipped path remains:
- `pipeline.model: tomato_legacy`
- `pipeline.partition_policy: tomics`

The architecture study adds opt-in research seams and a staged factorial program to answer the next design question:

Should the next TOMICS-Alloc architecture stay as a pure sink-partition policy with bounded root correction, or should it gain an explicit tomato reserve/buffer seam plus richer fruit and vegetative structure?

## Stable vs research boundary

Stable shipped behavior:
- `partition_policy: tomics`
- legacy fruit anchoring through one common assimilate pool
- greenhouse-safe bounded root correction
- LAI-band canopy protection
- no fruit-abortion or explicit reserve/buffer promotion into the shipped default

Research-only behavior:
- `partition_policy: tomics_alloc_research`
- source-derived architecture factors under `src/stomatal_optimiaztion/domains/tomato/tomics/alloc/components/partitioning/`
- staged architecture study runner:
  `scripts/run_tomics_allocation_factorial.py`

## Source backbone

Primary local source families reviewed:
- TOMSIM / Heuvelink 1996
- TOMGRO / Jones et al. 1991
- De Koning 1994
- Vanthoor 2011 article plus electronic appendix
- Kuijpers 2019

Secondary local source families used only after the tomato corpus:
- Potkay / THORP 2021
- related THORP-G / TDGM / GOH sources for bounded secondary context

Kuijpers is used as the architecture scaffold, not as a physiology replacement. The current study maps architecture blocks to:
- photosynthesis: `p`
- growth respiration: `gr`
- maintenance respiration: `m`
- assimilate buffer: `xA`
- assimilate partitioning: `g`
- biomass states: `xS`
- fruit harvest: `h1`
- leaf harvest: `h2`

## Current research seams

Added research modules:
- `research_modes.py`
- `research_policy.py`
- `reserve_buffer.py`
- `fruit_feedback.py`
- `root_modes.py`
- `common_structure.py`

These seams exist to support architecture screening only. They do not change the shipped `tomics` policy unless the research policy key is selected explicitly.

## Reduced factorial design

Stage 0:
- replay the shipped compare runner
- replay the shipped TOMICS screening factorial

Stage 1:
- source-derived candidate architectures across dry, moderate, and wet substrate states
- candidate families:
  - shipped default TOMICS
  - TOMSIM-like storage candidate
  - De Koning canopy-demand candidate
  - Vanthoor buffer candidate
  - TOMGRO feedback candidate
  - Kuijpers-scaffolded hybrid candidate

Stage 2:
- one-at-a-time parameter perturbations around shortlisted research candidates
- no full cartesian sweep

Stage 3:
- confirmation matrix across:
  - legacy
  - raw THORP-like
  - shipped TOMICS
  - selected research candidate
- wet, moderate, and dry root-zone scenarios
- baseline and high fruit-load proxy scenarios

## Canopy collapse definition

`canopy_collapse_days` is counted as:
- days with active fruiting
- and either `LAI < canopy_lai_floor`
- or `alloc_frac_leaf < leaf_fraction_floor`

The current study config uses:
- `canopy_lai_floor = 2.0`
- `leaf_fraction_floor = 0.18`

## Current recommendation

Keep the shipped default unchanged.

Recommended next architecture target:
- Kuijpers-scaffolded hybrid candidate
- TOMSIM/legacy fruit anchoring retained
- De Koning-style vegetative-demand pressure
- reduced TOMSIM-like storage seam
- bounded hysteretic THORP root correction
- buffered-daily temporal coupling
- canopy governor kept on

Current selected research family from the bundled study:
- `kuijpers_hybrid_candidate`
- the exact stage-2 parameterization is recorded in
  `out/tomics/analysis/allocation-factorial/selected_architecture.json`

Recommendation status:
- research-only
- not ready to replace shipped `tomics`

Reason:
- it improves the architecture study score while preserving fruit anchoring and avoiding canopy-collapse days
- but it still mixes components across source families and therefore inherits Kuijpers's non-identifiability warning

## What remains out of shipped default

Keep research-only:
- explicit storage/buffer accounting
- fruit-abortion or source-demand fruit-set feedback
- TOMGRO independent SLA driver
- Vanthoor fixed boxcar fruit train
- stem/root lumping as the main shipped root representation
- any THORP-root hysteresis beyond bounded explicit greenhouse correction

## Integration points

Live namespace:
- `src/stomatal_optimiaztion/domains/tomato/tomics/`

Stable allocation policy:
- `src/stomatal_optimiaztion/domains/tomato/tomics/alloc/components/partitioning/tomics_policy.py`

Research allocation policy:
- `src/stomatal_optimiaztion/domains/tomato/tomics/alloc/components/partitioning/research_policy.py`

Study runner:
- `scripts/run_tomics_allocation_factorial.py`

Study config:
- `configs/exp/tomics_allocation_factorial.yaml`

Study outputs:
- `out/tomics/analysis/allocation-factorial/`

## Output bundle

The study writes:
- `design_table.csv`
- `run_metrics.csv`
- `interaction_summary.csv`
- `candidate_ranking.csv`
- `selected_architecture.json`
- `decision_bundle.md`
- `summary_plot.png`
- `main_effects.png`
- `equation_traceability.csv`

## Example config

```yaml
pipeline:
  model: tomato_legacy
  partition_policy: tomics_alloc_research
  allocation_scheme: 4pool
  theta_substrate: 0.33
  partition_policy_params:
    architecture_id: kuijpers_hybrid_candidate
    fruit_structure_mode: tomsim_truss_cohort
    fruit_partition_mode: legacy_sink_exact
    vegetative_demand_mode: dekoning_vegetative_unit
    reserve_buffer_mode: tomsim_storage_pool
    fruit_feedback_mode: off
    thorp_root_correction_mode: bounded_hysteretic
```

## Linked review records

- `docs/architecture/review/tomics-allocation-primary-source-review.md`
- `docs/architecture/review/tomics-allocation-equation-manifest.md`
- `docs/architecture/review/tomics-allocation-gap-analysis.md`
- `docs/architecture/review/equation_manifest.md`
- `docs/architecture/review/source_traceability.md`
- `docs/architecture/review/source_manifest.csv`
