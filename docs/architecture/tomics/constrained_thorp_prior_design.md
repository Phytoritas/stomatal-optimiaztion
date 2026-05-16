# Constrained THORP Prior Design

The constrained THORP prior is a bounded latent-inference prior for TOMICS-HAF
2025-2C. It is not a raw allocator and cannot write final tomato allocation
directly.

THORP contributes only a hydraulic/root tendency inside residual vegetative
redistribution. The tomato fruit-vs-vegetative split stays anchored by the
tomato-first sink gate. THORP cannot override fruit sink priority and cannot be
promoted as a raw allocator.

The bounded THORP path applies:

- biological floors for fruit, leaf, stem, and root
- biological caps for fruit, leaf, stem, and root
- a wet-root cap when `RZI_main` is below the wet threshold
- a root stress gate before root allocation can increase above the legacy
  tomato prior
- LAI or explicit LAI-proxy protection for leaf allocation
- sum-to-one normalization after every constraint pass

The hybrid `tomato_constrained_thorp_prior` starts from the legacy tomato
fruit-vs-vegetative split, applies bounded THORP only to vegetative
redistribution, then re-applies the tomato constraints. Low-pass memory is
applied later by the inference layer per loadcell/treatment/prior family.

This design preserves the shipped TOMICS incumbent. It creates offline latent
allocation artifacts for later analysis; it does not change
`partition_policy: tomics`.
