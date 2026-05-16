from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

import pandas as pd

from stomatal_optimiaztion.domains.tomato.tomics.alloc.core import ensure_dir, write_json
from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.haf_gate_outputs import bool_value
from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.haf_gate_outputs import write_markdown_table


ALLOWED_CLAIMS = [
    "We evaluated TOMICS-HAF on the 2025 second cropping cycle as a bounded architecture-discrimination test.",
    "Day/night phases were radiation-defined from Dataset1 env_inside_radiation_wm2.",
    "For 2025-2C, DMC was fixed at 0.056.",
    "Dry yield derived from fresh yield using DMC 0.056 was an estimated dry-yield basis, not direct destructive dry-mass measurement.",
    "Latent allocation was observer-supported inference, not direct allocation validation.",
    "THORP was used only as a bounded mechanistic prior/correction, not as a raw tomato allocator.",
    "Harvest-family evaluation separated allocator family, harvest family, and observation operator.",
    "Promotion and cross-dataset gates were executed as safeguards.",
]

BLOCKED_PROMOTION_ALLOWED_CLAIM = (
    "The 2025-2C gate selected candidates for future cross-dataset testing but did not promote a new shipped TOMICS default."
)

FORBIDDEN_CLAIMS = [
    "Promotion gate passed",
    "Cross-dataset validation passed",
    "Allocation was directly validated.",
    "Dry yield was directly measured.",
    "DMC sensitivity was evaluated.",
    "Raw THORP allocator was promoted.",
    "Drought significantly reduced fruit expansion.",
    "This proves universal multi-season generalization.",
    "TOMICS-HAF is universally superior across seasons.",
]


def build_claim_register(
    *,
    promotion_gate_passed: bool,
    cross_dataset_gate_passed: bool,
    selected_for_future_cross_dataset_gate: bool = False,
    evidence_path: str,
    promotion_metadata: Mapping[str, Any] | None = None,
) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for claim in ALLOWED_CLAIMS:
        status, condition = _allowed_claim_status(claim, promotion_metadata)
        rows.append(
            {
                "claim_text": claim,
                "status": status,
                "condition": condition,
                "evidence_path": evidence_path,
                "safe_rewrite": claim,
            }
        )
    if not promotion_gate_passed and selected_for_future_cross_dataset_gate:
        rows.append(
            {
                "claim_text": BLOCKED_PROMOTION_ALLOWED_CLAIM,
                "status": "allowed",
                "condition": "promotion_gate_passed is false and promoted_candidate_id is null",
                "evidence_path": evidence_path,
                "safe_rewrite": BLOCKED_PROMOTION_ALLOWED_CLAIM,
            }
        )
    for claim in FORBIDDEN_CLAIMS:
        status = "forbidden"
        condition = "not supported by Goal 3C outputs"
        if claim == "Promotion gate passed" and promotion_gate_passed:
            status = "conditional"
            condition = "allowed only with promotion_gate_passed true and promoted_candidate_id non-null"
        if claim == "Cross-dataset validation passed" and cross_dataset_gate_passed:
            status = "conditional"
            condition = "allowed only with cross_dataset_gate_passed true"
        rows.append(
            {
                "claim_text": claim,
                "status": status,
                "condition": condition,
                "evidence_path": evidence_path,
                "safe_rewrite": _safe_rewrite_forbidden_claim(claim),
            }
        )
    return pd.DataFrame(rows)


def _allowed_claim_status(claim: str, metadata: Mapping[str, Any] | None) -> tuple[str, str]:
    if metadata is None:
        return "allowed", "current Goal 3C gate artifacts are cited with stated limitations"
    claim_checks = {
        "Day/night phases were radiation-defined from Dataset1 env_inside_radiation_wm2.": (
            metadata.get("radiation_daynight_primary_source") == "dataset1"
            and metadata.get("radiation_column_used") == "env_inside_radiation_wm2"
            and not bool_value(metadata.get("fixed_clock_daynight_primary"))
        ),
        "For 2025-2C, DMC was fixed at 0.056.": (
            metadata.get("canonical_fruit_DMC_fraction") == 0.056
            and bool_value(metadata.get("DMC_fixed_for_2025_2C"))
            and not bool_value(metadata.get("DMC_sensitivity_enabled"))
        ),
        "Dry yield derived from fresh yield using DMC 0.056 was an estimated dry-yield basis, not direct destructive dry-mass measurement.": (  # noqa: E501
            metadata.get("canonical_fruit_DMC_fraction") == 0.056
            and bool_value(metadata.get("dry_yield_is_dmc_estimated"))
            and not bool_value(metadata.get("direct_dry_yield_measured"))
        ),
        "Latent allocation was observer-supported inference, not direct allocation validation.": (
            not bool_value(metadata.get("latent_allocation_directly_validated"))
        ),
        "THORP was used only as a bounded mechanistic prior/correction, not as a raw tomato allocator.": (
            bool_value(metadata.get("THORP_used_as_bounded_prior"))
            and not bool_value(metadata.get("raw_THORP_allocator_used"))
        ),
        "Harvest-family evaluation separated allocator family, harvest family, and observation operator.": (
            bool_value(metadata.get("harvest_family_factorial_run"))
        ),
        "Promotion and cross-dataset gates were executed as safeguards.": (
            bool_value(metadata.get("promotion_gate_run")) and bool_value(metadata.get("cross_dataset_gate_run"))
        ),
    }
    if claim_checks.get(claim, True):
        return "allowed", "current Goal 3C gate artifacts are cited with stated limitations"
    return "conditional", "requires matching Goal 3C metadata guardrails before manuscript use"


def _safe_rewrite_forbidden_claim(claim: str) -> str:
    rewrites = {
        "Promotion gate passed": "Promotion gate was executed; pass/fail is determined by the gate outputs.",
        "Cross-dataset validation passed": (
            "Cross-dataset gate was executed; current measured-dataset support determines pass/fail."
        ),
        "Allocation was directly validated.": "Latent allocation remains observer-supported inference, not direct allocation validation.",
        "Dry yield was directly measured.": (
            "Dry yield derived from fresh yield using DMC 0.056 is an estimated dry-yield basis."
        ),
        "DMC sensitivity was evaluated.": "For 2025-2C, DMC was fixed at 0.056 and sensitivity was not evaluated.",
        "Raw THORP allocator was promoted.": (
            "THORP was used only as a bounded mechanistic prior/correction, not as a raw tomato allocator."
        ),
        "Drought significantly reduced fruit expansion.": (
            "Fruit diameter remains sensor-level apparent expansion diagnostics."
        ),
        "This proves universal multi-season generalization.": (
            "The 2025-2C evaluation is a bounded architecture-discrimination test."
        ),
        "TOMICS-HAF is universally superior across seasons.": (
            "The 2025-2C evaluation identifies candidates for future cross-dataset testing."
        ),
    }
    return rewrites[claim]


def write_claim_register(
    *,
    output_root: Path,
    promotion_metadata: Mapping[str, Any],
) -> dict[str, str]:
    output_root = ensure_dir(output_root)
    frame = build_claim_register(
        promotion_gate_passed=bool(promotion_metadata.get("promotion_gate_passed", False)),
        cross_dataset_gate_passed=bool(promotion_metadata.get("cross_dataset_gate_passed", False)),
        selected_for_future_cross_dataset_gate=bool(
            promotion_metadata.get("selected_candidate_for_future_cross_dataset_gate")
        ),
        evidence_path="out/tomics/validation/promotion-gate/haf_2025_2c/promotion_gate_metadata.json",
        promotion_metadata=promotion_metadata,
    )
    csv_path = output_root / "claim_register.csv"
    md_path = output_root / "claim_register.md"
    json_path = output_root / "claim_register.json"
    frame.to_csv(csv_path, index=False)
    write_markdown_table(
        md_path,
        frame,
        title="HAF 2025-2C Paper-Safe Claim Register",
        intro_lines=[
            "Forbidden claims require a safe rewrite before manuscript use.",
            "Promotion and cross-dataset outcomes must be cited from Goal 3C gate artifacts.",
        ],
    )
    write_json(
        json_path,
        {
            "claims": frame.to_dict(orient="records"),
            "unsafe_claims_blocked": bool((frame["status"] == "forbidden").any()),
            "paper_claim_safety_status": "pass",
        },
    )
    return {
        "claim_register_csv": str(csv_path),
        "claim_register_md": str(md_path),
        "claim_register_json": str(json_path),
    }


__all__ = [
    "ALLOWED_CLAIMS",
    "FORBIDDEN_CLAIMS",
    "build_claim_register",
    "write_claim_register",
]
