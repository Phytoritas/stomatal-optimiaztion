# TOMICS-HAF 2025-2C Future Cross-Dataset Plan

The next promotion opportunity requires compatible measured HAF evidence beyond `haf_2025_2c`.

## Minimum Evidence Requirement

- Add at least one additional compatible measured dataset.
- Use the same HAF observer/harvest basis or explicitly validate compatibility.
- Preserve the dry-yield contract: DMC fixed at `0.056` for 2025-2C and measured-vs-estimated provenance recorded per dataset.
- Keep proxy or legacy public datasets diagnostic-only unless separately validated as compatible measured HAF datasets.

## Gate Requirements

Before any shipped default change is proposed:

1. Regenerate per-dataset HAF harvest-family outputs.
2. Run cross-dataset gate with at least two compatible measured datasets.
3. Re-run promotion gate.
4. Confirm `cross_dataset_gate_passed = true`.
5. Confirm `promotion_gate_passed = true` and `promoted_candidate_id` is non-null.
6. Open a separate explicit shipped-default-change PR.

Until those criteria pass, `partition_policy: tomics` and the shipped TOMICS incumbent remain unchanged.
