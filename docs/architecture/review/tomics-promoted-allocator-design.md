# TOMICS Promoted Allocator Design

## Status

This design is implemented as a research-only allocator family behind:

- `partition_policy: tomics_promoted_research`

It does not replace the shipped meaning of `partition_policy: tomics`.

## Research concept

The promoted family lifts the constrained marginal allocator into a first-class study factor.

Conceptual form:

- `u_fruit = legacy_fruit_gate(...)`
- `p0_veg = normalize([p_leaf0, p_stem0, p_root0])`
- `u*_veg = prior_weighted_softmax(p0_veg, beta, DeltaM)`
- optional low-pass memory: `du_veg/dt = (u*_veg - u_veg) / tau_alloc`

The implementation keeps three hard constraints:

1. fruit remains anchored to the legacy sink gate
2. THORP remains bounded to subordinate root correction
3. missing stress signals fall back toward safe tomato behavior

## Structural factors

The promoted study elevates these factors:

- `optimizer_mode`
- `vegetative_prior_mode`
- `leaf_marginal_mode`
- `stem_marginal_mode`
- `root_marginal_mode`
- `fruit_feedback_mode`
- `reserve_buffer_mode`
- `canopy_governor_mode`
- `temporal_mode`
- `thorp_root_correction_mode`
- `allocation_scheme`

## Marginal logic

### Leaf

Leaf marginal is canopy-first.

Primary signals:

- LAI target gap
- weak low-sink penalty only in opt-in variants
- turnover cost only in stronger research variants

### Stem

Stem marginal is tomato support/transport/canopy-positioning.

Primary signals:

- fruit-load support
- transport demand proxy from VPD plus truss activity
- canopy-position deficit in the strongest research variant

### Root

Root marginal is greenhouse-rootzone stress gated.

Primary signals:

- water-supply stress
- root-zone multistress proxy
- root-zone saturation penalty

This is not a tree root-foraging allocator.

## Prior weighting

Vegetative allocation is not a free softmax.

The prior remains dominant when marginal signals are weak:

- `current_tomics_prior`
- `legacy_empirical_prior`
- `fit_from_warmup_prior`

This keeps the promoted family tomato-first rather than sink-chasing or tree-like.

## Research seams

The promoted family can optionally activate:

- TOMSIM-like storage pool
- Vanthoor-like carbohydrate buffer seam
- TOMGRO / De Koning fruit-feedback proxies
- bounded hysteretic THORP root correction

These seams remain research-only and are never silently activated by shipped TOMICS.

## Current actual-data outcome

On the current KNU validation slice, the promoted winner was:

- `constrained_full_plus_feedback__lai_target_center_3p0`

This candidate remains research-only because:

- it does not beat shipped TOMICS on measured-yield fit
- it loses the fruit anchor too strongly
- it still produces canopy-collapse pressure in confirmation runs
