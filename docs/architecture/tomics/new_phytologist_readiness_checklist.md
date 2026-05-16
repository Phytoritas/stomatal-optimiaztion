# New Phytologist Readiness Checklist

For the 2025-2C TOMICS-HAF analysis, fruit DMC is fixed at `0.056`.

Readiness items for yield provenance:

- Fresh yield basis is reported.
- DMC-estimated dry yield basis is reported with DMC `0.056`.
- Dry yield derived from fresh yield using DMC `0.056` is explicitly described as estimated, not direct destructive dry-mass measurement unless separately verified.
- DMC sensitivity is disabled for the current 2025-2C run unless explicitly re-enabled in a later goal.
- Any prior `0.065` DMC references are deprecated previous-default notes and must not drive 2025-2C metrics.
- Harvest-family ranking, observation operators, and promotion gate must use DMC `0.056` for 2025-2C.

Observer constraints remain:

- Day/night phases remain radiation-defined from Dataset1 `env_inside_radiation_wm2`, not fixed `06:00-18:00`.
- Fruit diameter remains sensor-level apparent expansion diagnostics.
- Latent allocation remains observer-supported inference, not direct allocation validation.
- Shipped TOMICS incumbent remains unchanged.

Goal 3B readiness additions:

- Harvest-family evaluation is a bounded 2025-2C architecture-discrimination test, not universal multi-season generalization.
- Latent allocation is allowed only as a research candidate input.
- THORP is allowed only as a bounded mechanistic prior/correction, not as a raw tomato allocator.
- Final promotion and cross-dataset validation remain separate future gates.
- Budget parity is knob-count and hidden-calibration-budget parity, not wall-clock compute-budget parity.
- Goal 3C readiness requires a reproducibility manifest and a Plotkit render manifest or rendered bundle status before the promotion gate is considered.
