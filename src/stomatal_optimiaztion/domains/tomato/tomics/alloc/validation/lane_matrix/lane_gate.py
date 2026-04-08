from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

import pandas as pd

from stomatal_optimiaztion.domains.tomato.tomics.alloc.core import ensure_dir, write_json
from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.cross_dataset_gate import (
    cross_dataset_proxy_guardrail,
)
from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.lane_matrix.artifact_schema import (
    LaneMatrixArtifactPaths,
)
from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.lane_matrix.lane_scorecard import (
    promotion_audit_passes,
)


def _as_dict(raw: object) -> dict[str, Any]:
    if isinstance(raw, dict):
        return {str(key): value for key, value in raw.items()}
    return {}


def _resolve_artifact_path(raw: str | Path, *, repo_root: Path) -> Path:
    candidate = Path(raw)
    if candidate.is_absolute():
        return candidate
    return (repo_root / candidate).resolve()


def _gate_config(config: dict[str, Any]) -> dict[str, Any]:
    validation_cfg = _as_dict(config.get("validation"))
    return _as_dict(validation_cfg.get("lane_matrix_gate"))


def _gate_score(row: pd.Series) -> float:
    rmse_cumulative = float(pd.to_numeric(pd.Series([row.get("rmse_cumulative_offset", math.inf)]), errors="coerce").fillna(math.inf).iloc[0])
    rmse_daily = float(pd.to_numeric(pd.Series([row.get("rmse_daily_increment", math.inf)]), errors="coerce").fillna(math.inf).iloc[0])
    fruit_anchor_error = float(pd.to_numeric(pd.Series([row.get("fruit_anchor_error", math.inf)]), errors="coerce").fillna(math.inf).iloc[0])
    canopy_collapse_days = float(pd.to_numeric(pd.Series([row.get("canopy_collapse_days", math.inf)]), errors="coerce").fillna(math.inf).iloc[0])
    return -rmse_cumulative - 0.5 * rmse_daily - 0.25 * fruit_anchor_error - 0.1 * canopy_collapse_days


def _base_promotion_mask(scorecard_df: pd.DataFrame) -> pd.Series:
    return (
        scorecard_df["promotion_eligible"].fillna(False).astype(bool)
        & ~scorecard_df["reference_only"].fillna(False).astype(bool)
        & scorecard_df["dataset_role"].eq("measured_harvest")
    )


def _lane_audit_summary(promotion_rows: pd.DataFrame) -> pd.DataFrame:
    if promotion_rows.empty:
        return pd.DataFrame(
            columns=[
                "allocation_lane_id",
                "harvest_profile_id",
                "lane_any_audit_failure",
                "lane_failed_dataset_count",
                "lane_failed_dataset_ids",
                "clean_dataset_count",
            ]
        )
    work = promotion_rows.copy()
    work["row_promotion_audit_pass"] = work.apply(promotion_audit_passes, axis=1)
    summary_rows: list[dict[str, object]] = []
    for (allocation_lane_id, harvest_profile_id), group in work.groupby(
        ["allocation_lane_id", "harvest_profile_id"],
        as_index=False,
    ):
        failed_rows = group.loc[~group["row_promotion_audit_pass"]].copy()
        summary_rows.append(
            {
                "allocation_lane_id": allocation_lane_id,
                "harvest_profile_id": harvest_profile_id,
                "lane_any_audit_failure": not failed_rows.empty,
                "lane_failed_dataset_count": int(failed_rows["dataset_id"].nunique()),
                "lane_failed_dataset_ids": json.dumps(
                    sorted({str(value) for value in failed_rows["dataset_id"]}),
                    sort_keys=True,
                ),
                "clean_dataset_count": int(group.loc[group["row_promotion_audit_pass"], "dataset_id"].nunique()),
            }
        )
    return pd.DataFrame(summary_rows)


def run_lane_matrix_gate(
    config: dict[str, Any],
    *,
    repo_root: Path,
    config_path: Path,
) -> dict[str, object]:
    gate_cfg = _gate_config(config)
    matrix_root = ensure_dir(
        _resolve_artifact_path(
            gate_cfg.get("matrix_root", "out/tomics/validation/lane-matrix"),
            repo_root=repo_root,
        )
    )
    output_root = ensure_dir(
        _resolve_artifact_path(
            gate_cfg.get("output_root", str(matrix_root)),
            repo_root=repo_root,
        )
    )
    paths = LaneMatrixArtifactPaths(output_root)
    scorecard_path = matrix_root / "lane_scorecard.csv"
    scorecard_df = pd.read_csv(scorecard_path)
    diagnostic_surface_df = scorecard_df.copy()
    diagnostic_surface_df["diagnostic_score"] = diagnostic_surface_df.apply(_gate_score, axis=1)
    diagnostic_surface_df = diagnostic_surface_df.sort_values(
        ["dataset_id", "diagnostic_score", "allocation_lane_id"],
        ascending=[True, False, True],
    ).reset_index(drop=True)
    diagnostic_surface_df.to_csv(paths.diagnostic_surface_path, index=False)

    promotion_input_rows = scorecard_df.loc[_base_promotion_mask(scorecard_df)].copy()
    lane_audit_df = _lane_audit_summary(promotion_input_rows)
    promotion_surface_df = pd.DataFrame(
        columns=[
            "allocation_lane_id",
            "harvest_profile_id",
            "mean_rmse_cumulative_offset",
            "mean_rmse_daily_increment",
            "mean_fruit_anchor_error",
            "max_canopy_collapse_days",
            "mean_native_family_state_fraction",
            "mean_proxy_family_state_fraction",
            "mean_shared_tdvs_proxy_fraction",
            "dataset_count",
            "dataset_win_count",
            "dataset_ids",
            "cross_dataset_stability_score",
            "winner_native_state_coverage",
            "winner_proxy_state_fraction",
            "winner_shared_tdvs_proxy_fraction",
            "winner_proxy_heavy_flag",
            "single_dataset_only_flag",
            "winner_not_promotion_grade_due_to_proxy_dependence",
            "winner_not_promotion_grade_due_to_cross_dataset_instability",
            "lane_any_audit_failure",
            "lane_failed_dataset_count",
            "lane_failed_dataset_ids",
            "clean_dataset_count",
            "passes",
        ]
    )
    selected_promotion: dict[str, object] = {}
    if not promotion_input_rows.empty:
        promotion_candidates = promotion_input_rows.loc[
            promotion_input_rows.apply(promotion_audit_passes, axis=1)
        ].copy()
    else:
        promotion_candidates = pd.DataFrame()
    measured_dataset_count = int(promotion_candidates["dataset_id"].dropna().nunique()) if not promotion_candidates.empty else 0
    if not promotion_candidates.empty:
        promotion_candidates["gate_score"] = promotion_candidates.apply(_gate_score, axis=1)
        dataset_winners = (
            promotion_candidates.sort_values(
                ["dataset_id", "gate_score", "allocation_lane_id"],
                ascending=[True, False, True],
            )
            .groupby("dataset_id", as_index=False)
            .first()[["dataset_id", "allocation_lane_id", "harvest_profile_id"]]
        )
        dataset_winners["dataset_win_flag"] = True
        promotion_candidates = promotion_candidates.merge(
            dataset_winners,
            on=["dataset_id", "allocation_lane_id", "harvest_profile_id"],
            how="left",
        )
        promotion_candidates["dataset_win_flag"] = promotion_candidates["dataset_win_flag"].fillna(False).astype(bool)
        promotion_surface_df = (
            promotion_candidates.groupby(["allocation_lane_id", "harvest_profile_id"], as_index=False)
            .agg(
                mean_rmse_cumulative_offset=("rmse_cumulative_offset", "mean"),
                mean_rmse_daily_increment=("rmse_daily_increment", "mean"),
                mean_fruit_anchor_error=("fruit_anchor_error", "mean"),
                max_canopy_collapse_days=("canopy_collapse_days", "max"),
                mean_native_family_state_fraction=("native_state_coverage", "mean"),
                mean_proxy_family_state_fraction=("mean_proxy_family_state_fraction", "mean"),
                mean_shared_tdvs_proxy_fraction=("shared_tdvs_proxy_fraction", "mean"),
                dataset_count=("dataset_id", "nunique"),
                dataset_win_count=("dataset_win_flag", "sum"),
                dataset_ids=("dataset_id", lambda values: json.dumps(sorted({str(value) for value in values}), sort_keys=True)),
            )
            .sort_values(["mean_rmse_cumulative_offset", "mean_rmse_daily_increment"], ascending=[True, True])
            .reset_index(drop=True)
        )
        promotion_surface_df = promotion_surface_df.merge(
            lane_audit_df,
            on=["allocation_lane_id", "harvest_profile_id"],
            how="left",
        )
        denominator = max(measured_dataset_count, 1)
        promotion_surface_df["cross_dataset_stability_score"] = (
            promotion_surface_df["dataset_win_count"].astype(float) / float(denominator)
        )
        guardrail_rows: list[dict[str, object]] = []
        for _, row in promotion_surface_df.iterrows():
            guardrail = cross_dataset_proxy_guardrail(
                row,
                native_state_coverage_min=float(gate_cfg.get("native_state_coverage_min", 0.5)),
                shared_tdvs_proxy_fraction_max=float(gate_cfg.get("shared_tdvs_proxy_fraction_max", 0.5)),
                cross_dataset_stability_score_min=float(gate_cfg.get("cross_dataset_stability_score_min", 0.5)),
                min_dataset_count=int(gate_cfg.get("min_dataset_count", 2)),
                measured_dataset_count=measured_dataset_count,
            )
            candidate = {**row.to_dict(), **guardrail}
            candidate["passes"] = bool(candidate["passes"]) and not bool(candidate.get("lane_any_audit_failure", False))
            guardrail_rows.append(candidate)
        promotion_surface_df = pd.DataFrame(guardrail_rows).sort_values(
            ["passes", "mean_rmse_cumulative_offset", "mean_rmse_daily_increment"],
            ascending=[False, True, True],
        )
    elif not lane_audit_df.empty:
        promotion_surface_df = lane_audit_df.copy()
        promotion_surface_df["mean_rmse_cumulative_offset"] = math.nan
        promotion_surface_df["mean_rmse_daily_increment"] = math.nan
        promotion_surface_df["mean_fruit_anchor_error"] = math.nan
        promotion_surface_df["max_canopy_collapse_days"] = math.nan
        promotion_surface_df["mean_native_family_state_fraction"] = math.nan
        promotion_surface_df["mean_proxy_family_state_fraction"] = math.nan
        promotion_surface_df["mean_shared_tdvs_proxy_fraction"] = math.nan
        promotion_surface_df["dataset_count"] = 0
        promotion_surface_df["dataset_win_count"] = 0
        promotion_surface_df["dataset_ids"] = "[]"
        promotion_surface_df["cross_dataset_stability_score"] = 0.0
        promotion_surface_df["winner_native_state_coverage"] = 0.0
        promotion_surface_df["winner_proxy_state_fraction"] = 0.0
        promotion_surface_df["winner_shared_tdvs_proxy_fraction"] = 0.0
        promotion_surface_df["winner_proxy_heavy_flag"] = False
        promotion_surface_df["single_dataset_only_flag"] = True
        promotion_surface_df["winner_not_promotion_grade_due_to_proxy_dependence"] = False
        promotion_surface_df["winner_not_promotion_grade_due_to_cross_dataset_instability"] = True
        promotion_surface_df["passes"] = False
        promotion_surface_df = promotion_surface_df[
            [
                "allocation_lane_id",
                "harvest_profile_id",
                "mean_rmse_cumulative_offset",
                "mean_rmse_daily_increment",
                "mean_fruit_anchor_error",
                "max_canopy_collapse_days",
                "mean_native_family_state_fraction",
                "mean_proxy_family_state_fraction",
                "mean_shared_tdvs_proxy_fraction",
                "dataset_count",
                "dataset_win_count",
                "dataset_ids",
                "cross_dataset_stability_score",
                "winner_native_state_coverage",
                "winner_proxy_state_fraction",
                "winner_shared_tdvs_proxy_fraction",
                "winner_proxy_heavy_flag",
                "single_dataset_only_flag",
                "winner_not_promotion_grade_due_to_proxy_dependence",
                "winner_not_promotion_grade_due_to_cross_dataset_instability",
                "lane_any_audit_failure",
                "lane_failed_dataset_count",
                "lane_failed_dataset_ids",
                "clean_dataset_count",
                "passes",
            ]
        ]
    if not promotion_surface_df.empty:
        promotion_surface_df["lane_any_audit_failure"] = promotion_surface_df["lane_any_audit_failure"].fillna(False).astype(bool)
        promotion_surface_df["lane_failed_dataset_count"] = pd.to_numeric(
            promotion_surface_df["lane_failed_dataset_count"],
            errors="coerce",
        ).fillna(0).astype(int)
        promotion_surface_df["clean_dataset_count"] = pd.to_numeric(
            promotion_surface_df["clean_dataset_count"],
            errors="coerce",
        ).fillna(0).astype(int)
        if not promotion_surface_df.empty:
            selected_promotion = promotion_surface_df.iloc[0].to_dict()
    promotion_surface_df.to_csv(paths.promotion_surface_path, index=False)

    diagnostic_selected = diagnostic_surface_df.iloc[0].to_dict() if not diagnostic_surface_df.empty else {}
    decision_payload = {
        "matrix_root": str(matrix_root),
        "promotion_surface_path": str(paths.promotion_surface_path),
        "diagnostic_surface_path": str(paths.diagnostic_surface_path),
        "measured_dataset_count": measured_dataset_count,
        "guardrails": {
            "native_state_coverage_min": float(gate_cfg.get("native_state_coverage_min", 0.5)),
            "shared_tdvs_proxy_fraction_max": float(gate_cfg.get("shared_tdvs_proxy_fraction_max", 0.5)),
            "cross_dataset_stability_score_min": float(gate_cfg.get("cross_dataset_stability_score_min", 0.5)),
            "min_dataset_count": int(gate_cfg.get("min_dataset_count", 2)),
        },
        "promotion_selected": selected_promotion,
        "promotion_blocked": (not bool(selected_promotion)) or (not bool(selected_promotion.get("passes", False))),
        "diagnostic_selected": diagnostic_selected,
    }
    write_json(paths.lane_gate_decision_path, decision_payload)
    return {
        "output_root": str(output_root),
        "promotion_rows": int(promotion_surface_df.shape[0]),
        "diagnostic_rows": int(diagnostic_surface_df.shape[0]),
    }


__all__ = ["run_lane_matrix_gate"]
