# RALPH Completion Report

- generated_at_utc: `2026-05-16T14:01:15Z`
- goal_id: `ralph-goal-3c-tomics-haf-2025-2c-promotion-and-cross-dataset-gate-outputs-with-single-dataset-promotion-block-new-phytologist-readiness-matrix-and-paper-safe-claim-register`
- status: `done`
- iterations_used: `2`

## Goal

Goal 3C TOMICS-HAF 2025-2C promotion and cross-dataset gate outputs with single-dataset promotion block, New Phytologist readiness matrix, and paper-safe claim register

## Evidence

- Branch: `feat/tomics-haf-2025-2c-promotion-gate`
- Head source: Use `git rev-parse HEAD` or `gh pr view 315 --json headRefOid` for the current PR head; tracked RAH state does not hardcode its containing commit hash.
- Issue: `#314`
- PR: `#315` stacked on `feat/tomics-haf-2025-2c-harvest-family-eval`
- Promotion gate executed and blocked as `blocked_cross_dataset_evidence_insufficient`.
- Cross-dataset gate executed and blocked as `blocked_insufficient_measured_datasets` with measured dataset count `1` and required measured dataset count `2`.
- `promoted_candidate_id` remains `null` and `shipped_TOMICS_incumbent_changed = false`.
- Claim register and New Phytologist readiness matrix outputs were generated under `out/` and intentionally not committed.
- Targeted Goal 3C tests: `17 passed`.
- Goal 3B.5 regression subset: `17 passed`.
- Full pytest: `702 passed, 26 skipped, 12 deselected`.
- Ruff: passed.
- `git diff --check` and staged diff check: passed.
- Final reviewer pass: no high-severity findings; RAH state avoids self-referential fixed HEAD values.

## Remaining Block

A shipped TOMICS default change remains blocked until compatible cross-dataset evidence passes in a separate explicit promotion-change task.
