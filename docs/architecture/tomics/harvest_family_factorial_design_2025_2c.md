# TOMICS-HAF 2025-2C Harvest-Family Factorial Design

Goal 3B remains blocked until it is explicitly started. This document records the DMC precondition for that later goal.

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
