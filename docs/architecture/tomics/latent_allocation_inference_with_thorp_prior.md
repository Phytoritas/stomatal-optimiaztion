# TOMICS-HAF 2025-2C Latent Allocation Inference With THORP Prior

Goal 3A uses the Goal 2.5 production observer feature frame as its input. The
input precondition is explicit: production observer export must be complete, row
caps must be absent, chunk aggregation must be used, and day/night phases must
remain radiation-defined from Dataset1 `env_inside_radiation_wm2`.

Latent allocation inference is not direct allocation validation without organ
partition observations. The 2025-2C observer frame provides radiation-defined
ET, root-zone stress, apparent conductance, fruit/leaf observers, and Dataset3
structural/phenology diagnostics, but it does not provide observed organ
partitioning. Metadata therefore records:

- `direct_partition_observation_available = false`
- `allocation_validation_basis = latent_inference_from_observer_features`
- `latent_allocation_directly_validated = false`
- `latent_allocation_promotable_by_itself = false`

THORP is used only as a bounded mechanistic prior or correction. Raw THORP
allocation is forbidden as final tomato allocation, is not promoted, and cannot
replace the shipped TOMICS incumbent.

The tomato-first fruit-vs-vegetative gate remains primary. THORP can only
redistribute residual vegetative allocation among leaf, stem, and root after the
tomato fruit gate is preserved. Root allocation increase is stress-gated by
`RZI_main`, leaf allocation collapse is guarded by a biological floor, and wet
root excess is guarded by a wet-condition cap.

LAI is unavailable in the Goal 2.5 observer frame. Goal 3A does not fabricate
LAI. It may compute an explicit LAI proxy only when configured, and the proxy is
used only for leaf-protection diagnostics and bounded inference.

Fruit diameter remains sensor-level apparent expansion diagnostics. It is not
used for p-values, allocation calibration, hydraulic gate calibration, or model
promotion.

For the 2025-2C TOMICS-HAF analysis, fruit DMC is fixed at `0.056`. Dry
yield derived from fresh yield using DMC `0.056` is an estimated dry-yield
basis, not direct destructive dry-mass measurement unless separately verified.
DMC sensitivity is disabled for the current 2025-2C run unless explicitly
re-enabled in a later goal. Any prior `0.065` DMC references are deprecated
previous-default notes and must not drive latent metadata, harvest-family
ranking, or promotion metrics.

Goal 3A does not run harvest-family factorials, cross-dataset promotion gates,
or promotion gates. Those remain blocked for later explicit goals.
