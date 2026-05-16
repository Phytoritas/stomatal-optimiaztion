# TOMICS-HAF 2025-2C Harvest-Family Factorial Design

Goal 3B runs a bounded 2025-2C harvest-family architecture-discrimination test
from the production observer feature frame and latent allocation posterior. It
does not run the final promotion gate and does not run the cross-dataset gate.

For the 2025-2C TOMICS-HAF analysis, fruit DMC is fixed at `0.056`.

The 2025-2C observation operator family must include:

- `fresh_to_dry_dmc_0p056`
- `dry_to_fresh_dmc_0p056`

Goal 3B acceptance criteria:

- DMC default = `0.056`.
- DMC fixed output exists.
- Fresh and DMC-estimated dry yield bases are both reported.
- DMC sensitivity outputs are not required for the current 2025-2C run.

DMC sensitivity is disabled for the current 2025-2C run unless explicitly re-enabled in a later goal. Any prior `0.065` DMC references are deprecated previous-default notes and must not drive 2025-2C metrics.

Dry yield derived from fresh yield using DMC `0.056` is an estimated dry-yield basis, not direct destructive dry-mass measurement unless separately verified.

Harvest-family ranking, observation operators, and promotion gate must use DMC `0.056` for 2025-2C.

## Goal 3B staged design

- HF0 replays the shipped TOMICS incumbent with the DMC `0.056` observation operator.
- HF1 screens fruit and leaf harvest families with the shipped allocator fixed.
- HF2 evaluates allocator families against the bounded harvest shortlist.
- HF3 performs one-axis-at-a-time parameter screening.
- HF4 writes the budget-parity audit.
- HF5 and HF6 remain disabled in this goal.

The HAF runner uses `constant_0p056` only. The previous 6.5 percent constant
mode and DMC sensitivity mode are forbidden for current 2025-2C primary metrics.

Latent allocation posterior rows may enter only through the
`tomics_haf_latent_allocation_research` allocator family. This is a research
candidate input, not direct allocation validation.
