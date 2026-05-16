from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.haf_goal4a_evidence_package import (
    MERGE_ORDER,
    build_goal4a_decision_metadata,
    build_pr_stack_merge_readiness_rows,
)


def _pr(number: int, base: str, head: str, body: str = "## Validation\npytest passed"):
    return {
        "number": number,
        "title": f"PR {number}",
        "state": "OPEN",
        "baseRefName": base,
        "headRefName": head,
        "headRefOid": f"sha-{number}",
        "mergeStateStatus": "CLEAN",
        "isDraft": False,
        "body": body,
        "closingIssuesReferences": [],
    }


def test_goal4a_pr_stack_merge_readiness_preserves_order_and_blocks_default_change():
    frame = build_pr_stack_merge_readiness_rows(
        [
            _pr(309, "main", "fix/308-diagnose-tomics-daily-harvest-increments"),
            _pr(
                311,
                "fix/308-diagnose-tomics-daily-harvest-increments",
                "feat/tomics-haf-2025-2c-latent-allocation",
            ),
            _pr(
                313,
                "feat/tomics-haf-2025-2c-latent-allocation",
                "feat/tomics-haf-2025-2c-harvest-family-eval",
            ),
            _pr(
                315,
                "feat/tomics-haf-2025-2c-harvest-family-eval",
                "feat/tomics-haf-2025-2c-promotion-gate",
                body="Closes #314\n\n## Validation\npytest passed",
            ),
        ]
    )

    assert frame["pr_number"].tolist() == MERGE_ORDER
    assert frame["allowed_to_merge_order_index"].tolist() == [1, 2, 3, 4]
    assert frame["depends_on"].tolist() == ["", "#309", "#311", "#313"]
    assert frame["merge_blockers"].eq("").all()
    assert frame["out_artifacts_committed"].eq(False).all()
    assert frame["raw_data_committed"].eq(False).all()
    assert frame["shipped_TOMICS_incumbent_changed"].eq(False).all()
    assert frame.loc[frame["pr_number"].eq(315), "closes_issue"].item() == "#314"

    decision = build_goal4a_decision_metadata(
        promotion_gate_passed=False,
        cross_dataset_gate_passed=False,
        measured_dataset_count=1,
        required_measured_dataset_count=2,
    )
    assert decision["shipped_default_change_recommended"] is False
    assert decision["shipped_default_change_blocked"] is True
    assert decision["promotion_remains_blocked"] is True


def test_goal4a_pr_stack_merge_readiness_blocks_unsafe_claims():
    frame = build_pr_stack_merge_readiness_rows(
        [
            _pr(309, "main", "fix/308-diagnose-tomics-daily-harvest-increments"),
            _pr(
                311,
                "fix/308-diagnose-tomics-daily-harvest-increments",
                "feat/tomics-haf-2025-2c-latent-allocation",
            ),
            _pr(
                313,
                "feat/tomics-haf-2025-2c-latent-allocation",
                "feat/tomics-haf-2025-2c-harvest-family-eval",
            ),
            _pr(
                315,
                "feat/tomics-haf-2025-2c-harvest-family-eval",
                "feat/tomics-haf-2025-2c-promotion-gate",
                body="Closes #314\n\nPromotion gate passed\n\n## Validation\npytest passed",
            ),
        ]
    )

    row = frame.loc[frame["pr_number"].eq(315)].iloc[0]
    assert not bool(row["unsafe_claims_absent"])
    assert "unsafe_claims_present" in row["merge_blockers"]


def test_goal4a_pr_stack_merge_readiness_blocks_all_frozen_forbidden_claims():
    body = "\n".join(
        [
            "Closes #314",
            "## Validation",
            "pytest passed",
            "TOMICS-HAF is universally superior across seasons.",
            "A shipped TOMICS default was changed.",
        ]
    )
    frame = build_pr_stack_merge_readiness_rows(
        [
            _pr(309, "main", "fix/308-diagnose-tomics-daily-harvest-increments"),
            _pr(
                311,
                "fix/308-diagnose-tomics-daily-harvest-increments",
                "feat/tomics-haf-2025-2c-latent-allocation",
            ),
            _pr(
                313,
                "feat/tomics-haf-2025-2c-latent-allocation",
                "feat/tomics-haf-2025-2c-harvest-family-eval",
            ),
            _pr(
                315,
                "feat/tomics-haf-2025-2c-harvest-family-eval",
                "feat/tomics-haf-2025-2c-promotion-gate",
                body=body,
            ),
        ]
    )

    row = frame.loc[frame["pr_number"].eq(315)].iloc[0]
    assert not bool(row["unsafe_claims_absent"])
    assert "unsafe_claims_present" in row["merge_blockers"]


def test_goal4a_pr_stack_merge_readiness_blocks_unmergeable_state_and_private_artifacts():
    dirty_pr = _pr(
        315,
        "feat/tomics-haf-2025-2c-harvest-family-eval",
        "feat/tomics-haf-2025-2c-promotion-gate",
        body="Closes #314\n\n## Validation\npytest passed",
    )
    dirty_pr["mergeStateStatus"] = "DIRTY"
    frame = build_pr_stack_merge_readiness_rows(
        [
            _pr(309, "main", "fix/308-diagnose-tomics-daily-harvest-increments"),
            _pr(
                311,
                "fix/308-diagnose-tomics-daily-harvest-increments",
                "feat/tomics-haf-2025-2c-latent-allocation",
            ),
            _pr(
                313,
                "feat/tomics-haf-2025-2c-latent-allocation",
                "feat/tomics-haf-2025-2c-harvest-family-eval",
            ),
            dirty_pr,
        ],
        tracked_out_paths=["out/leaked_private_result.csv"],
        raw_data_committed=True,
    )

    row = frame.loc[frame["pr_number"].eq(315)].iloc[0]
    assert "merge_state_dirty" in row["merge_blockers"]
    assert "out_artifacts_committed" in row["merge_blockers"]
    assert "raw_data_committed" in row["merge_blockers"]
