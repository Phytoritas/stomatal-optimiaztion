# Wakeup Packet

## Identity
- workspace: `stomatal-optimiaztion`
- topic: `architecture-refactor`
- sessionId: `stomatal-optimiaztion#adhoc:tomics-haf-2025-2c-promotion-gate`
- caseId: `case/stomatal-optimiaztion/adhoc/tomics-haf-2025-2c-promotion-gate`
- issue: `#314`
- pull_request: `#315`
- branch: `feat/tomics-haf-2025-2c-promotion-gate`
- head: `c889d426982369ae74cfde0894ebd2c5d0cffbbc`

## Current State
- current_stage: `tomics-haf-2025-2c-goal-3c-promotion-gate-pr315-open`
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
8. `configs/exp/tomics_haf_2025_2c_promotion_gate.yaml`
9. `configs/exp/tomics_haf_2025_2c_cross_dataset_gate.yaml`
10. `.rah/state/status.json`
11. `.rah/state/gates.json`
12. `.rah/plans/current_loop.md`
13. `.rah/ralph/goal.json`
14. `.rah/ralph/loop_state.json`
15. `.rah/ralph/completion_report.md`

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

## Goal 3C Completed Facts
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
- Targeted Goal 3C tests: `16 passed`.
- Goal 3B.5 regression subset: `17 passed`.
- Full pytest: `701 passed, 26 skipped, 12 deselected`.
- Ruff: passed.
- Diff checks: passed.
- Final reviewer pass: no blocking or medium findings.

## Memento Start Recipe
```python
context(
    types=["preference", "procedure", "error", "decision"],
    workspace="stomatal-optimiaztion",
    sessionId="stomatal-optimiaztion#adhoc:tomics-haf-2025-2c-promotion-gate",
)
recall(
    keywords=["stomatal-optimiaztion", "TOMICS-HAF", "Goal 3C", "promotion gate", "cross-dataset", "PR #315"],
    topic="architecture-refactor",
    workspace="stomatal-optimiaztion",
    sessionId="stomatal-optimiaztion#adhoc:tomics-haf-2025-2c-promotion-gate",
    caseMode=True,
    depth="high-level",
    contextText="TOMICS-HAF 2025_2C Goal 3C promotion/cross-dataset gate PR #315 restart",
)
```
