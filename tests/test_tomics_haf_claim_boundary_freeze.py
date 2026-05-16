from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.haf_goal4a_evidence_package import (
    ALLOWED_PRIMARY_CLAIMS,
    FORBIDDEN_CLAIMS,
    build_claim_boundary_freeze_rows,
)


def test_goal4a_claim_boundary_freezes_allowed_and_forbidden_claims():
    frame = build_claim_boundary_freeze_rows(
        promotion_gate_passed=False,
        cross_dataset_gate_passed=False,
        shipped_default_changed=False,
    )

    assert set(ALLOWED_PRIMARY_CLAIMS).issubset(set(frame["claim_text"]))
    assert set(FORBIDDEN_CLAIMS).issubset(set(frame["claim_text"]))
    forbidden = frame.loc[frame["claim_text"].isin(FORBIDDEN_CLAIMS)]
    assert forbidden["status"].eq("forbidden").all()
    assert forbidden["safe_rewrite"].astype(str).str.len().gt(0).all()
    assert (
        frame.loc[frame["claim_text"].eq("Promotion gate passed."), "status"].item()
        == "forbidden"
    )
    assert (
        frame.loc[frame["claim_text"].eq("A shipped TOMICS default was changed."), "safe_rewrite"]
        .item()
        .startswith("No shipped TOMICS default change")
    )
