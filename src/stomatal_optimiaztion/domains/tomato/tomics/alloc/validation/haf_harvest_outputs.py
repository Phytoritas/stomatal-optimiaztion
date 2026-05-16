from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

from stomatal_optimiaztion.domains.tomato.tomics.alloc.core import ensure_dir, write_json


OUTPUT_FILENAMES = {
    "design": "harvest_family_factorial_design.csv",
    "manifest": "harvest_family_run_manifest.csv",
    "metrics_pooled": "harvest_family_metrics_pooled.csv",
    "metrics_by_loadcell": "harvest_family_metrics_by_loadcell.csv",
    "metrics_mean_sd": "harvest_family_metrics_mean_sd.csv",
    "daily_overlay": "harvest_family_daily_overlay.csv",
    "cumulative_overlay": "harvest_family_cumulative_overlay.csv",
    "mass_balance": "harvest_family_mass_balance.csv",
    "budget_parity": "harvest_family_budget_parity.csv",
    "rankings": "harvest_family_rankings.csv",
    "selected": "harvest_family_selected_research_candidate.json",
    "promotion_csv": "harvest_family_prerequisite_promotion_summary.csv",
    "promotion_md": "harvest_family_prerequisite_promotion_summary.md",
    "metadata": "harvest_family_metadata.json",
    "observation_audit": "observation_operator_dmc_0p056_audit.csv",
    "stale_dmc_audit": "no_stale_dmc_0p065_primary_audit.csv",
}


def write_frame(path: Path, frame: pd.DataFrame) -> Path:
    ensure_dir(path.parent)
    frame.to_csv(path, index=False)
    return path


def prerequisite_promotion_summary(
    *,
    selected_candidate_id: str | None,
) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "promotion_gate_run": False,
                "promotion_gate_ready": False,
                "promotion_candidate_selected_for_future_gate": bool(
                    selected_candidate_id
                ),
                "selected_candidate_id": selected_candidate_id or "",
                "single_dataset_promotion_allowed": False,
                "cross_dataset_gate_required": True,
                "cross_dataset_gate_run": False,
                "shipped_TOMICS_incumbent_changed": False,
            }
        ]
    )


def write_prerequisite_promotion_markdown(
    path: Path,
    summary: pd.DataFrame,
) -> Path:
    row = summary.iloc[0].to_dict()
    text = "\n".join(
        [
            "# HAF 2025-2C Harvest-Family Promotion Prerequisite Summary",
            "",
            "- Promotion gate run: false",
            "- Promotion gate ready: false",
            "- Cross-dataset gate run: false",
            "- Single-dataset promotion allowed: false",
            "- Shipped TOMICS incumbent changed: false",
            f"- Future-gate research candidate selected: {str(row['selected_candidate_id'])}",
            "",
            "This file is a prerequisite summary only. It is not a final promotion-gate output.",
            "",
        ]
    )
    ensure_dir(path.parent)
    path.write_text(text, encoding="utf-8")
    return path


def stale_dmc_primary_audit(
    *,
    config: dict[str, Any],
    metadata: dict[str, Any],
    design_df: pd.DataFrame,
    input_metadata: dict[str, Any] | None = None,
) -> pd.DataFrame:
    observation_config = config.get("observation_operator", {})
    serialized = json.dumps(
        {
            "observation_operator_config": observation_config,
            "metadata": metadata,
            "fdmc_modes": sorted(set(design_df.get("fdmc_mode", []))),
        },
        sort_keys=True,
        default=str,
    )
    forbidden_hits = []
    for token in (
        "configured_default_fruit_dry_matter_content",
        "constant_0p065",
        "dmc_0p065",
        "DMC_sensitivity_enabled\": true",
    ):
        if token in serialized:
            forbidden_hits.append(token)
    current_primary_0p065 = (
        metadata.get("default_fruit_dry_matter_content") == 0.065
        or metadata.get("fruit_DMC_fraction") == 0.065
    )
    if current_primary_0p065:
        forbidden_hits.append("current_primary_0p065")
    upstream_hits = []
    input_metadata = input_metadata or {}
    if "configured_default_fruit_dry_matter_content" in input_metadata:
        upstream_hits.append("configured_default_fruit_dry_matter_content")
    if input_metadata.get("default_fruit_dry_matter_content") == 0.065:
        upstream_hits.append("upstream_default_fruit_dry_matter_content_0p065")
    if input_metadata.get("fruit_DMC_fraction") == 0.065:
        upstream_hits.append("upstream_fruit_DMC_fraction_0p065")
    if input_metadata.get("DMC_sensitivity_enabled") is True:
        upstream_hits.append("upstream_DMC_sensitivity_enabled_true")
    return pd.DataFrame(
        [
            {
                "audit_name": "no_stale_dmc_0p065_primary",
                "status": "pass" if not forbidden_hits else "fail",
                "forbidden_hits_json": json.dumps(forbidden_hits, sort_keys=True),
                "upstream_metadata_warning_hits_json": json.dumps(
                    upstream_hits,
                    sort_keys=True,
                ),
                "upstream_metadata_warning_count": len(upstream_hits),
                "deprecated_previous_default_fruit_DMC_fraction": metadata.get(
                    "deprecated_previous_default_fruit_DMC_fraction"
                ),
                "DMC_sensitivity_enabled": metadata.get("DMC_sensitivity_enabled"),
                "canonical_fruit_DMC_fraction": metadata.get(
                    "canonical_fruit_DMC_fraction"
                ),
            }
        ]
    )


def write_haf_harvest_outputs(
    *,
    output_root: Path,
    frames: dict[str, pd.DataFrame],
    selected_payload: dict[str, Any],
    metadata: dict[str, Any],
) -> dict[str, str]:
    output_root = ensure_dir(output_root)
    paths: dict[str, str] = {}
    for key, filename in OUTPUT_FILENAMES.items():
        path = output_root / filename
        if key == "selected":
            write_json(path, selected_payload)
        elif key == "metadata":
            write_json(path, metadata)
        elif key == "promotion_md":
            write_prerequisite_promotion_markdown(path, frames["promotion_csv"])
        else:
            frame = frames.get(key, pd.DataFrame())
            write_frame(path, frame)
        paths[key] = str(path)
    return paths


__all__ = [
    "OUTPUT_FILENAMES",
    "prerequisite_promotion_summary",
    "stale_dmc_primary_audit",
    "write_haf_harvest_outputs",
]
