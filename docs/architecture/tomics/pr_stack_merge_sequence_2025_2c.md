# TOMICS-HAF 2025-2C PR Stack Merge Sequence

Current stack:

1. PR #309: observer pipeline.
2. PR #311: latent allocation inference.
3. PR #313: harvest-family evaluation and Goal 3B.5 pre-gate polish.
4. Goal 3C promotion/cross-dataset gate PR.

Merge order must preserve the dependency stack. Do not merge Goal 3C before PR #309, PR #311, and PR #313 are ready.

Goal 3C may execute gates and still block promotion. A blocked promotion is a valid outcome and does not authorize changing the shipped TOMICS incumbent.

Post-merge follow-up, only if future cross-dataset criteria truly pass:

- Open a separate explicit promotion-change task.
- Propose any shipped `partition_policy: tomics` change in that separate PR.
- Re-run promotion and cross-dataset validation before changing shipped defaults.
