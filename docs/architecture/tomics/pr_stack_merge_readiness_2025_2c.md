# TOMICS-HAF 2025-2C PR Stack Merge Readiness

Goal 4A freezes merge-readiness for the current TOMICS-HAF 2025-2C stack. This is a packaging and evidence-readiness step only. It does not authorize a shipped TOMICS default change.

## Frozen Decision

- `promotion_gate_executed = true`
- `promotion_gate_passed = false`
- `cross_dataset_gate_executed = true`
- `cross_dataset_gate_passed = false`
- `measured_dataset_count = 1`
- `required_measured_dataset_count = 2`
- `shipped_default_change_recommended = false`
- `shipped_default_change_blocked_reason = cross_dataset_evidence_insufficient`

Promotion gate was executed and blocked promotion because compatible cross-dataset evidence is insufficient.

## Merge Order

| order | PR | title | base | head | status |
| --- | --- | --- | --- | --- | --- |
| 1 | #309 | [TOMICS] Add HAF 2025-2C observer pipeline | `main` | `fix/308-diagnose-tomics-daily-harvest-increments` | open, clean, non-draft |
| 2 | #311 | [TOMICS] Add HAF 2025-2C latent allocation inference | `fix/308-diagnose-tomics-daily-harvest-increments` | `feat/tomics-haf-2025-2c-latent-allocation` | open, clean, non-draft |
| 3 | #313 | [TOMICS] Add HAF 2025-2C harvest-family evaluation | `feat/tomics-haf-2025-2c-latent-allocation` | `feat/tomics-haf-2025-2c-harvest-family-eval` | open, clean, non-draft |
| 4 | #315 | [TOMICS] Add HAF 2025-2C promotion gate outputs | `feat/tomics-haf-2025-2c-harvest-family-eval` | `feat/tomics-haf-2025-2c-promotion-gate` | open, clean, non-draft |

PR #315 must not merge before PR #313. PR #313 must not merge before PR #311. PR #311 must not merge before PR #309. If a lower PR changes after merge or rebase, dependent PRs must be revalidated.

## Merge Blockers

No code-level merge blockers are recorded by Goal 4A. Remaining warnings are process-only:

- RAH SessionStart/Stop hooks are not registered. This is operational convenience, not a merge blocker.
- PR #315 is stacked and `closingIssuesReferences` may remain empty until the stack lands through the default branch. The PR body includes `Closes #314`.
- GitHub Project attachment failed from the current CLI context. This does not affect code correctness or merge-readiness.

## Guardrail Freeze

- No shipped TOMICS incumbent change is recommended.
- `partition_policy: tomics` remains unchanged.
- DMC remains fixed at `0.056`.
- Dry yield remains DMC-estimated, not direct destructive dry-mass measurement.
- Latent allocation remains observer-supported inference, not direct allocation validation.
- THORP remains a bounded mechanistic prior/correction, not a raw tomato allocator.
- Fruit diameter remains sensor-level apparent expansion diagnostics.

Private machine-readable readiness outputs are generated under:

```text
out/tomics/validation/promotion-gate/haf_2025_2c/pr_stack_merge_readiness.*
```
