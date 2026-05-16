# TOMICS Harvest-Aware Promotion Gate

The harvest-aware promotion gate is not run in Goal 3B. Goal 3B writes
prerequisite outputs only:

- `promotion_gate_run = false`
- `promotion_gate_ready = false`
- `single_dataset_promotion_allowed = false`
- `cross_dataset_gate_required = true`
- `cross_dataset_gate_run = false`
- `shipped_TOMICS_incumbent_changed = false`

For the later 2025-2C TOMICS-HAF promotion workflow, fruit DMC is fixed at `0.056`. Promotion-gate observation operators must use DMC `0.056` for fresh-to-dry and dry-to-fresh conversions.

Dry yield derived from fresh yield using DMC `0.056` is an estimated dry-yield basis, not direct destructive dry-mass measurement unless separately verified.

DMC sensitivity is disabled for the current 2025-2C run unless explicitly re-enabled in a later goal. DMC sensitivity outputs are not required for the current 2025-2C promotion precondition.

Any prior `0.065` DMC references are deprecated previous-default notes and must not drive 2025-2C promotion metrics.

Latent allocation remains observer-supported inference, not direct allocation validation.
