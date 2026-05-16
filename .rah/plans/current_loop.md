# Current Loop

## Earliest Restart Point
Stage 3C. TOMICS-HAF 2025-2C Promotion/Cross-Dataset Gate PR #315 Open

## Read First
- `AGENTS.md`
- `docs/architecture/Phytoritas.md`
- `docs/architecture/tomics/promotion_gate_2025_2c.md`
- `docs/architecture/tomics/cross_dataset_gate_2025_2c.md`
- `docs/architecture/tomics/claim_register_2025_2c.md`
- `docs/architecture/tomics/new_phytologist_readiness_checklist.md`
- `docs/architecture/tomics/pr_stack_merge_sequence_2025_2c.md`
- `configs/exp/tomics_haf_2025_2c_promotion_gate.yaml`
- `configs/exp/tomics_haf_2025_2c_cross_dataset_gate.yaml`
- `.rah/state/status.json`
- `.rah/state/gates.json`
- `.rah/memory/wakeup.md`
- `.rah/ralph/goal.json`
- `.rah/ralph/loop_state.json`
- `.rah/ralph/completion_report.md`

## Active Contract
- Promotion gate was executed; pass/fail is determined by the gate outputs.
- If the measured dataset count remains one, promotion is blocked by cross-dataset evidence insufficiency.
- For 2025-2C, DMC is fixed at 0.056.
- Dry yield derived from fresh yield using DMC 0.056 is an estimated dry-yield basis, not direct destructive dry-mass measurement.
- Latent allocation remains observer-supported inference, not direct allocation validation.
- THORP is used only as a bounded mechanistic prior/correction, not as a raw tomato allocator.
- Fruit diameter remains sensor-level apparent expansion diagnostics.
- Shipped TOMICS incumbent remains unchanged unless a separate promotion-change PR is explicitly approved.

## Next Actions
1. Review PR #315 after PR #309, PR #311, and PR #313 remain aligned in the stack.
2. Do not change shipped TOMICS defaults in this PR.
3. Treat Goal 3C as safeguard evidence: gate executed, promotion blocked, cross-dataset evidence insufficient.

## Goal 3C Completed Facts
- Issue #314 tracks TOMICS-HAF 2025-2C promotion and cross-dataset gate outputs.
- PR #315 is open from branch `feat/tomics-haf-2025-2c-promotion-gate` into `feat/tomics-haf-2025-2c-harvest-family-eval`.
- PR #315 head source: Use `git rev-parse HEAD` or `gh pr view 315 --json headRefOid` for the current PR head; tracked RAH state does not hardcode its containing commit hash.
- Promotion gate status is `blocked_cross_dataset_evidence_insufficient`.
- Cross-dataset gate status is `blocked_insufficient_measured_datasets`.
- `measured_dataset_count = 1`; `required_measured_dataset_count = 2`.
- `promoted_candidate_id = null`.
- `shipped_TOMICS_incumbent_changed = false`.
- Final validation: targeted Goal 3C tests `17 passed`; Goal 3B.5 regression `17 passed`; full pytest `702 passed, 26 skipped, 12 deselected`; Ruff passed; diff checks passed; reviewer pass clean.

<!-- RALPH MANAGED BLOCK START -->
## RALPH Goal Loop

- goal_id: `ralph-goal-3c-tomics-haf-2025-2c-promotion-and-cross-dataset-gate-outputs-with-single-dataset-promotion-block-new-phytologist-readiness-matrix-and-paper-safe-claim-register`
- status: `done`
- iteration: `2` / `6`
- loop_phase: `completed`
- implementation_gate: `slice-complete-promotion-change-blocked`
- blocked_reason: `None`

### Next Actions

- Review PR #315 in the stacked PR sequence.
- Keep shipped TOMICS default changes blocked until a separate explicit promotion-change task is approved after compatible cross-dataset evidence passes.

### State

- `.rah/ralph/goal.json`
- `.rah/ralph/loop_state.json`
- `.rah/ralph/iterations/`
- `.rah/ralph/completion_report.md`
<!-- RALPH MANAGED BLOCK END -->
