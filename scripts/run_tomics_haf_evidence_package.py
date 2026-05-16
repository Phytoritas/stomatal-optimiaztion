from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping

from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.haf_gate_outputs import bool_value
from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.haf_goal4a_evidence_package import (
    MERGE_ORDER,
    build_claim_boundary_freeze_rows,
    build_evidence_package_manifest,
    build_goal4a_decision_metadata,
    build_pr_stack_merge_readiness_rows,
    gh_pr_payloads,
    tracked_forbidden_artifacts,
    write_goal4a_evidence_package_outputs,
)


def _default_repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _required_int(metadata: Mapping[str, Any], key: str, *, metadata_path: Path) -> int:
    if key not in metadata:
        raise ValueError(f"Goal 4A requires {key} in promotion metadata: {metadata_path}")
    value = metadata.get(key)
    if isinstance(value, bool):
        raise ValueError(f"Goal 4A requires {key} to be a non-negative integer: {metadata_path}")
    if isinstance(value, int):
        parsed = value
    elif isinstance(value, float):
        if not value.is_integer():
            raise ValueError(f"Goal 4A requires {key} to be a non-negative integer: {metadata_path}")
        parsed = int(value)
    elif isinstance(value, str):
        normalized = value.strip()
        if not normalized.isdecimal():
            raise ValueError(f"Goal 4A requires {key} to be a non-negative integer: {metadata_path}")
        parsed = int(normalized)
    else:
        raise ValueError(f"Goal 4A requires {key} to be a non-negative integer: {metadata_path}")
    if parsed < 0:
        raise ValueError(f"Goal 4A requires {key} to be a non-negative integer: {metadata_path}")
    return parsed


def load_required_promotion_metadata(*, repo_root: Path, promotion_root: Path) -> dict[str, Any]:
    metadata_path = repo_root / promotion_root / "promotion_gate_metadata.json"
    if not metadata_path.exists():
        raise FileNotFoundError(
            "Goal 4A evidence package requires existing Goal 3C promotion metadata: "
            f"{metadata_path}"
        )
    raw = json.loads(metadata_path.read_text(encoding="utf-8"))
    if not isinstance(raw, Mapping):
        raise TypeError(f"Promotion metadata must be a mapping: {metadata_path}")
    metadata = {str(key): value for key, value in raw.items()}
    if not bool_value(metadata.get("promotion_gate_run")):
        raise ValueError(f"Promotion metadata does not record promotion_gate_run=true: {metadata_path}")
    if not bool_value(metadata.get("cross_dataset_gate_run")):
        raise ValueError(f"Promotion metadata does not record cross_dataset_gate_run=true: {metadata_path}")
    if bool_value(metadata.get("promotion_gate_passed")):
        raise ValueError(f"Goal 4A requires blocked promotion metadata, got promotion_gate_passed=true: {metadata_path}")
    if bool_value(metadata.get("cross_dataset_gate_passed")):
        raise ValueError(
            f"Goal 4A requires blocked cross-dataset metadata, got cross_dataset_gate_passed=true: {metadata_path}"
        )
    if metadata.get("promoted_candidate_id") not in {None, ""}:
        raise ValueError(f"Goal 4A requires promoted_candidate_id to be null/empty: {metadata_path}")
    if bool_value(metadata.get("shipped_TOMICS_incumbent_changed")):
        raise ValueError(f"Goal 4A requires shipped_TOMICS_incumbent_changed=false: {metadata_path}")
    if str(metadata.get("promotion_gate_status", "")).strip() != "blocked_cross_dataset_evidence_insufficient":
        raise ValueError(
            "Goal 4A requires promotion_gate_status=blocked_cross_dataset_evidence_insufficient: "
            f"{metadata_path}"
        )
    if str(metadata.get("cross_dataset_gate_status", "")).strip() != "blocked_insufficient_measured_datasets":
        raise ValueError(
            "Goal 4A requires cross_dataset_gate_status=blocked_insufficient_measured_datasets: "
            f"{metadata_path}"
        )
    measured_count = _required_int(metadata, "measured_dataset_count", metadata_path=metadata_path)
    required_count = _required_int(metadata, "required_measured_dataset_count", metadata_path=metadata_path)
    if required_count <= 0:
        raise ValueError(
            "Goal 4A requires required_measured_dataset_count to be positive: "
            f"{metadata_path}"
        )
    if measured_count >= required_count:
        raise ValueError(
            "Goal 4A requires measured_dataset_count to be below required_measured_dataset_count: "
            f"{metadata_path}"
        )
    return metadata


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate TOMICS-HAF 2025-2C Goal 4A evidence package outputs.")
    parser.add_argument("--repo-root", default=str(_default_repo_root()))
    parser.add_argument(
        "--promotion-root",
        required=True,
        help="Promotion-gate output root, usually out/tomics/validation/promotion-gate/haf_2025_2c.",
    )
    parser.add_argument(
        "--harvest-root",
        required=True,
        help="Harvest-family output root, usually out/tomics/validation/harvest-family/haf_2025_2c.",
    )
    parser.add_argument(
        "--latent-root",
        required=True,
        help="Latent allocation output root, usually out/tomics/validation/latent-allocation/haf_2025_2c.",
    )
    parser.add_argument(
        "--observer-root",
        required=True,
        help="Observer analysis root, usually out/tomics/analysis/haf_2025_2c.",
    )
    parser.add_argument(
        "--figures-root",
        default="out/tomics/figures/haf_2025_2c",
        help="Plotkit figure manifest root.",
    )
    args = parser.parse_args()

    repo_root = Path(args.repo_root).resolve()
    promotion_root = Path(args.promotion_root)
    promotion_metadata = load_required_promotion_metadata(repo_root=repo_root, promotion_root=promotion_root)
    tracked_artifacts = tracked_forbidden_artifacts(repo_root)
    pr_rows = build_pr_stack_merge_readiness_rows(
        gh_pr_payloads(MERGE_ORDER, repo_root=repo_root),
        tracked_out_paths=tracked_artifacts,
        raw_data_committed=False,
    )
    evidence_rows = build_evidence_package_manifest(
        repo_root=repo_root,
        promotion_root=promotion_root,
        harvest_root=Path(args.harvest_root),
        latent_root=Path(args.latent_root),
        observer_root=Path(args.observer_root),
        figures_root=Path(args.figures_root),
    )
    decision_metadata = build_goal4a_decision_metadata(
        promotion_gate_executed=bool_value(promotion_metadata.get("promotion_gate_run")),
        promotion_gate_passed=bool_value(promotion_metadata.get("promotion_gate_passed")),
        cross_dataset_gate_executed=bool_value(promotion_metadata.get("cross_dataset_gate_run")),
        cross_dataset_gate_passed=bool_value(promotion_metadata.get("cross_dataset_gate_passed")),
        measured_dataset_count=_required_int(
            promotion_metadata,
            "measured_dataset_count",
            metadata_path=repo_root / promotion_root / "promotion_gate_metadata.json",
        ),
        required_measured_dataset_count=_required_int(
            promotion_metadata,
            "required_measured_dataset_count",
            metadata_path=repo_root / promotion_root / "promotion_gate_metadata.json",
        ),
        shipped_tomics_incumbent_changed=bool_value(promotion_metadata.get("shipped_TOMICS_incumbent_changed")),
    )
    claim_rows = build_claim_boundary_freeze_rows(
        promotion_gate_passed=bool_value(promotion_metadata.get("promotion_gate_passed")),
        cross_dataset_gate_passed=bool_value(promotion_metadata.get("cross_dataset_gate_passed")),
        shipped_default_changed=bool_value(promotion_metadata.get("shipped_TOMICS_incumbent_changed")),
    )
    paths = write_goal4a_evidence_package_outputs(
        output_root=repo_root / promotion_root,
        pr_readiness=pr_rows,
        evidence_manifest=evidence_rows,
        claim_boundary=claim_rows,
        decision_metadata=decision_metadata,
    )
    print(json.dumps(paths, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
