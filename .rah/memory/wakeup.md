# Wakeup Packet

## Identity
- workspace: `stomatal-optimiaztion`
- topic: `architecture-refactor`
- sessionId: `stomatal-optimiaztion#adhoc:tomics-haf-2025-2c-promotion-gate`
- caseId: `case/stomatal-optimiaztion/adhoc/tomics-haf-2025-2c-promotion-gate`
- issue: `#314`
- pull_request: `#315`
- branch: `feat/tomics-haf-2025-2c-promotion-gate`
- head_source: Use `git rev-parse HEAD` or `gh pr view 315 --json headRefOid` for the current PR head; tracked RAH state does not hardcode its containing commit hash.

## Current State
- current_stage: `tomics-haf-2025-2c-goal-4a-merge-readiness-pr315-open`
- implementation_gate: `slice-complete-promotion-change-blocked`
- agents_and_workflow_gate: `pass`
- memory_freshness: `hydrated`
- RALPH status: `done`

## Read First
1. nearest `AGENTS.md`
2. `docs/architecture/Phytoritas.md`
3. `docs/architecture/tomics/promotion_gate_2025_2c.md`
4. `docs/architecture/tomics/cross_dataset_gate_2025_2c.md`
5. `docs/architecture/tomics/claim_register_2025_2c.md`
6. `docs/architecture/tomics/new_phytologist_readiness_checklist.md`
7. `docs/architecture/tomics/pr_stack_merge_sequence_2025_2c.md`
8. `docs/architecture/tomics/pr_stack_merge_readiness_2025_2c.md`
9. `docs/architecture/tomics/tomics_haf_2025_2c_evidence_package.md`
10. `docs/architecture/tomics/tomics_haf_2025_2c_claim_boundary_freeze.md`
11. `docs/manuscript/tomics_haf_2025_2c_methods_outline.md`
12. `configs/exp/tomics_haf_2025_2c_promotion_gate.yaml`
13. `configs/exp/tomics_haf_2025_2c_cross_dataset_gate.yaml`
14. `.rah/state/status.json`
15. `.rah/state/gates.json`
16. `.rah/plans/current_loop.md`
17. `.rah/ralph/goal.json`
18. `.rah/ralph/loop_state.json`
19. `.rah/ralph/completion_report.md`

## Non-Negotiable TOMICS-HAF Contract
- Preserve the intentional spelling `stomatal-optimiaztion` and `stomatal_optimiaztion`.
- For 2025-2C, DMC is fixed at 0.056.
- Dry yield derived from fresh yield using DMC 0.056 is an estimated dry-yield basis, not direct destructive dry-mass measurement.
- Latent allocation remains observer-supported inference, not direct allocation validation.
- THORP is used only as a bounded mechanistic prior/correction, not as a raw tomato allocator.
- Fruit diameter remains sensor-level apparent expansion diagnostics.
- Promotion gate was executed; pass/fail is determined by the gate outputs.
- If the measured dataset count remains one, promotion is blocked by cross-dataset evidence insufficiency.
- Shipped TOMICS incumbent remains unchanged unless a separate promotion-change PR is explicitly approved.

## Prior Gate Completed Facts
- PR #315 implements HAF 2025-2C promotion and cross-dataset gate outputs.
- Promotion gate was run and blocked: `blocked_cross_dataset_evidence_insufficient`.
- Cross-dataset gate was run and blocked: `blocked_insufficient_measured_datasets`.
- `measured_dataset_count = 1`; `required_measured_dataset_count = 2`.
- Best research candidate may be carried forward only for future cross-dataset testing.
- `promoted_candidate_id = null`.
- `shipped_TOMICS_incumbent_changed = false`.
- New Phytologist readiness is not pass-ready because promotion and cross-dataset categories remain blocked and Plotkit is manifest-only/partial.
- Claim register exists and unsafe claims are blocked.

## Validation Evidence
- Private promotion run: passed and wrote promotion outputs under `out/tomics/validation/promotion-gate/haf_2025_2c/`.
- Private cross-dataset run: passed and wrote cross-dataset outputs under `out/tomics/validation/multi-dataset/haf_2025_2c/`.
- Targeted gate regression tests: `17 passed`.
- Targeted Goal 4A tests: `11 passed`.
- Goal 3B.5 regression subset: `17 passed`.
- Full pytest: `713 passed, 26 skipped, 12 deselected`.
- Ruff: passed.
- Diff checks: passed.
- Final reviewer pass: no blocking or medium findings.

## Goal 4A Completed Facts
- PR stack merge-readiness docs and private outputs were generated.
- Evidence package manifest was generated for observer, latent allocation, harvest-family, promotion/cross-dataset, and figure evidence.
- Claim boundary freeze and manuscript/thesis outline docs were created.
- Process warnings are documented as non-blocking.
- No shipped TOMICS default change is recommended.

## Memento Start Recipe
```python
context(
    types=["preference", "procedure", "error", "decision"],
    workspace="stomatal-optimiaztion",
    sessionId="stomatal-optimiaztion#adhoc:tomics-haf-2025-2c-promotion-gate",
)
recall(
    keywords=["stomatal-optimiaztion", "TOMICS-HAF", "Goal 4A", "merge-readiness", "evidence package", "PR #315"],
    topic="architecture-refactor",
    workspace="stomatal-optimiaztion",
    sessionId="stomatal-optimiaztion#adhoc:tomics-haf-2025-2c-promotion-gate",
    caseMode=True,
    depth="high-level",
    contextText="TOMICS-HAF 2025_2C Goal 4A merge-readiness evidence package PR #315 restart",
)
```
