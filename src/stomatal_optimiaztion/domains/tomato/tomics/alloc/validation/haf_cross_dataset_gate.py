from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

import pandas as pd

from stomatal_optimiaztion.domains.tomato.tomics.alloc.core import ensure_dir, write_json
from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.haf_gate_outputs import (
    as_dict,
    bool_value,
    float_value,
    int_value,
    read_json,
    resolve_artifact_path,
    write_key_value_csv,
    write_markdown_table,
)


CROSS_DATASET_BLOCKER = "cross_dataset_evidence_insufficient"


def _dataset_scorecard_rows(
    cfg: Mapping[str, Any],
    *,
    repo_root: Path,
    config_path: Path | None,
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for item in cfg.get("available_dataset_outputs", []) or []:
        item_cfg = as_dict(item)
        dataset_id = str(item_cfg.get("dataset_id", "unknown"))
        metadata_path = resolve_artifact_path(
            str(item_cfg.get("harvest_family_metadata", "")),
            repo_root=repo_root,
            config_path=config_path,
        )
        metadata: dict[str, Any] = {}
        metadata_exists = metadata_path.exists()
        if metadata_exists:
            metadata = read_json(metadata_path, artifact_label=f"{dataset_id} harvest_family_metadata")
        measured_or_proxy = str(item_cfg.get("measured_or_proxy", "measured"))
        dataset_type = str(item_cfg.get("dataset_type", "haf_measured_actual"))
        dmc_basis = float_value(metadata.get("canonical_fruit_DMC_fraction"), default=float("nan"))
        compatible_observation_operator = (
            metadata_exists
            and dmc_basis == 0.056
            and bool_value(metadata.get("dry_yield_is_dmc_estimated"))
            and not bool_value(metadata.get("direct_dry_yield_measured"))
        )
        explicitly_proxy = measured_or_proxy != "measured"
        contributes = bool(
            metadata_exists
            and measured_or_proxy == "measured"
            and compatible_observation_operator
            and bool_value(item_cfg.get("contributes_to_promotion_gate", True), default=True)
        )
        if not metadata_exists:
            reason = "missing_harvest_family_metadata"
        elif explicitly_proxy:
            reason = "proxy_dataset_diagnostic_only"
        elif not compatible_observation_operator:
            reason = "incompatible_observation_operator_or_dmc_basis"
        elif not contributes:
            reason = "excluded_by_config"
        else:
            reason = ""
        rows.append(
            {
                "dataset_id": dataset_id,
                "dataset_type": dataset_type,
                "measured_or_proxy": measured_or_proxy,
                "compatible_observation_operator": compatible_observation_operator,
                "dmc_basis": dmc_basis if metadata_exists else "",
                "contributes_to_promotion_gate": contributes,
                "reason_if_excluded": reason,
                "metadata_path": str(metadata_path),
            }
        )
    seen_dataset_ids: set[str] = set()
    seen_metadata_paths: set[str] = set()
    for row in rows:
        row["unique_measured_dataset"] = False
        if not row["contributes_to_promotion_gate"]:
            continue
        dataset_key = str(row["dataset_id"]).casefold()
        metadata_key = str(Path(str(row["metadata_path"])).resolve()).casefold()
        if dataset_key in seen_dataset_ids or metadata_key in seen_metadata_paths:
            row["contributes_to_promotion_gate"] = False
            row["reason_if_excluded"] = "duplicate_dataset_or_artifact"
            continue
        seen_dataset_ids.add(dataset_key)
        seen_metadata_paths.add(metadata_key)
        row["unique_measured_dataset"] = True
    return rows


def build_haf_cross_dataset_gate_payload(
    *,
    config: Mapping[str, Any],
    repo_root: Path,
    config_path: Path | None = None,
) -> dict[str, Any]:
    cfg = as_dict(config.get("cross_dataset_gate"))
    required_count = int_value(cfg.get("require_measured_dataset_count_min"), default=2)
    rows = _dataset_scorecard_rows(cfg, repo_root=repo_root, config_path=config_path)
    scorecard = pd.DataFrame(rows)
    measured_count = int(scorecard["contributes_to_promotion_gate"].sum()) if not scorecard.empty else 0
    measured_dataset_ids = (
        scorecard.loc[scorecard["contributes_to_promotion_gate"], "dataset_id"].astype(str).tolist()
        if not scorecard.empty
        else []
    )
    passed = measured_count >= required_count
    status = "passed" if passed else "blocked_insufficient_measured_datasets"
    blockers = [] if passed else [CROSS_DATASET_BLOCKER]
    metadata = {
        "current_dataset_id": str(cfg.get("current_dataset_id", "haf_2025_2c")),
        "cross_dataset_gate_run": True,
        "cross_dataset_gate_passed": passed,
        "cross_dataset_gate_status": status,
        "measured_dataset_count": measured_count,
        "required_measured_dataset_count": required_count,
        "measured_dataset_ids": measured_dataset_ids,
        "blockers": blockers,
        "allow_legacy_or_public_proxy_for_promotion": bool_value(
            cfg.get("allow_legacy_or_public_proxy_for_promotion"),
            default=False,
        ),
        "proxy_dataset_use": str(cfg.get("proxy_dataset_use", "diagnostic_only")),
        "single_dataset_promotion_allowed": bool_value(
            cfg.get("single_dataset_promotion_allowed"),
            default=False,
        ),
        "promotion_block_reasons": blockers,
    }
    return {
        "scorecard": scorecard,
        "metadata": metadata,
    }


def write_haf_cross_dataset_gate_outputs(
    *,
    output_root: Path,
    payload: Mapping[str, Any],
) -> dict[str, str]:
    output_root = ensure_dir(output_root)
    scorecard = payload["scorecard"]
    if not isinstance(scorecard, pd.DataFrame):
        scorecard = pd.DataFrame(scorecard)
    metadata = as_dict(payload.get("metadata"))
    scorecard_path = output_root / "cross_dataset_scorecard.csv"
    summary_csv_path = output_root / "cross_dataset_gate_summary.csv"
    summary_md_path = output_root / "cross_dataset_gate_summary.md"
    metadata_path = output_root / "cross_dataset_metadata.json"
    blockers_path = output_root / "cross_dataset_blockers.csv"
    scorecard.to_csv(scorecard_path, index=False)
    write_key_value_csv(summary_csv_path, metadata)
    write_json(metadata_path, metadata)
    blocker_rows = [{"blocker_code": blocker, "blocking": True} for blocker in metadata.get("blockers", [])]
    pd.DataFrame(blocker_rows, columns=["blocker_code", "blocking"]).to_csv(blockers_path, index=False)
    write_markdown_table(
        summary_md_path,
        pd.DataFrame(
            [
                {
                    "cross_dataset_gate_run": metadata["cross_dataset_gate_run"],
                    "cross_dataset_gate_passed": metadata["cross_dataset_gate_passed"],
                    "cross_dataset_gate_status": metadata["cross_dataset_gate_status"],
                    "measured_dataset_count": metadata["measured_dataset_count"],
                    "required_measured_dataset_count": metadata["required_measured_dataset_count"],
                    "blockers": ", ".join(metadata.get("blockers", [])) or "none",
                }
            ]
        ),
        title="HAF 2025-2C Cross-Dataset Gate",
        intro_lines=[
            "A blocked cross-dataset gate is a valid safeguard outcome.",
            "Legacy or proxy datasets do not contribute to promotion unless explicitly validated as compatible measured datasets.",
        ],
    )
    return {
        "cross_dataset_scorecard": str(scorecard_path),
        "cross_dataset_gate_summary_csv": str(summary_csv_path),
        "cross_dataset_gate_summary_md": str(summary_md_path),
        "cross_dataset_metadata": str(metadata_path),
        "cross_dataset_blockers": str(blockers_path),
    }


def run_haf_cross_dataset_gate(
    config: Mapping[str, Any],
    *,
    repo_root: Path,
    config_path: Path,
) -> dict[str, Any]:
    cfg = as_dict(config.get("cross_dataset_gate"))
    output_root = resolve_artifact_path(
        str(cfg.get("output_root", "out/tomics/validation/multi-dataset/haf_2025_2c")),
        repo_root=repo_root,
        config_path=config_path,
        prefer_repo_root=True,
    )
    payload = build_haf_cross_dataset_gate_payload(config=config, repo_root=repo_root, config_path=config_path)
    paths = write_haf_cross_dataset_gate_outputs(output_root=output_root, payload=payload)
    return {
        **paths,
        "output_root": str(output_root),
        "metadata": payload["metadata"],
    }


__all__ = [
    "CROSS_DATASET_BLOCKER",
    "build_haf_cross_dataset_gate_payload",
    "run_haf_cross_dataset_gate",
    "write_haf_cross_dataset_gate_outputs",
]
