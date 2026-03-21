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

Hard constraints:

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

Leaf marginal remains canopy-first.

Primary signals:

- LAI target gap
- weak low-sink penalty only in opt-in variants
- turnover cost only in stronger research variants

### Stem

Stem marginal remains tomato support, transport, and canopy-positioning.

Primary signals:

- fruit-load support
- transport demand proxy from VPD plus truss activity
- canopy-position deficit in the strongest research variant

### Root

Root marginal remains greenhouse-rootzone stress gated.

Primary signals:

- water-supply stress
- root-zone multistress proxy
- root-zone saturation penalty

This is not a tree root-foraging allocator.

## Optional research seams

The promoted family can activate:

- TOMSIM-like storage pool
- Vanthoor-like carbohydrate buffer seam
- TOMGRO or De Koning fruit-feedback proxies
- bounded hysteretic THORP root correction

These seams remain research-only and are never silently activated by shipped TOMICS.

## Current baseline winner

The current promoted-study winner is:

- `constrained_full_plus_feedback__buffer_capacity_g_m2_12p0`

## Fair-validation conclusion

The fair KNU promotion gate keeps the promoted allocator research-only because:

- it does not pass the fruit-anchor guardrail
- it still shows non-zero canopy-collapse pressure
- shipped TOMICS remains the incumbent under the full promotion gate

The promoted allocator therefore remains a research candidate rather than a shipped-default candidate.
