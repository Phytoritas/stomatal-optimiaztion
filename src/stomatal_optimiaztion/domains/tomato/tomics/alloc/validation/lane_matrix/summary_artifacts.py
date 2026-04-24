from __future__ import annotations

import math

import pandas as pd

from stomatal_optimiaztion.domains.tomato.tomics.alloc.core import write_json
from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.lane_matrix.allocation_lane_registry import (
    ResolvedAllocationLane,
)
from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.lane_matrix.artifact_schema import (
    LaneMatrixArtifactPaths,
)
from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.lane_matrix.dataset_role_registry import (
    ResolvedDatasetRole,
)


ARCHITECTURE_CODE_BY_LANE = {
    "legacy_sink_baseline": "A1",
    "raw_reference_thorp": "A2",
    "incumbent_current": "A3",
    "research_promoted": "A4",
}

ARCHITECTURE_FAMILY_BY_LANE = {
    "legacy_sink_baseline": "legacy_sink_baseline",
    "raw_reference_thorp": "raw_thorp_direct_negative_control",
    "incumbent_current": "shipped_tomics_bounded_incumbent",
    "research_promoted": "research_promoted_marginal_allocator",
}


def architecture_code(lane_id: str) -> str:
    return ARCHITECTURE_CODE_BY_LANE.get(lane_id, "unmapped")


def architecture_family_id(lane_id: str) -> str:
    return ARCHITECTURE_FAMILY_BY_LANE.get(lane_id, lane_id)


def _json_ready(value: object) -> object:
    if value is pd.NA:
        return None
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        return None
    if isinstance(value, (pd.Timestamp,)):
        return value.isoformat()
    if hasattr(value, "item"):
        try:
            return _json_ready(value.item())
        except (TypeError, ValueError):
            pass
    return value


def _json_tree(value: object) -> object:
    if isinstance(value, dict):
        return {str(key): _json_tree(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_json_tree(item) for item in value]
    return _json_ready(value)


def _numeric(row: pd.Series, column: str, default: float = math.nan) -> float:
    value = pd.to_numeric(pd.Series([row.get(column, default)]), errors="coerce").iloc[0]
    return float(value) if pd.notna(value) else math.nan


def _bool(row: pd.Series, column: str) -> bool:
    value = row.get(column, False)
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"true", "1", "yes"}


def _column_equals(frame: pd.DataFrame, column: str, expected: str) -> pd.Series:
    if column not in frame:
        return pd.Series([False] * len(frame), index=frame.index)
    return frame[column].fillna("").astype(str).eq(expected)


def _direct_measured_mask(frame: pd.DataFrame) -> pd.Series:
    base = _column_equals(frame, "dataset_role", "measured_harvest")
    if "evidence_grade" in frame:
        base &= _column_equals(frame, "evidence_grade", "direct_measured_harvest")
    if "decision_weight" in frame:
        base &= _column_equals(frame, "decision_weight", "promotion_gate")
    return base


def _review_only_derived_dw_mask(frame: pd.DataFrame) -> pd.Series:
    return _column_equals(frame, "evidence_grade", "review_only_derived_dw")


def _guardrail_failures(row: pd.Series) -> list[str]:
    failures: list[str] = []
    if _bool(row, "any_all_zero_harvest_series"):
        failures.append("all_zero_harvest_series")
    if _bool(row, "offplant_with_positive_mass_flag"):
        failures.append("offplant_with_positive_mass")
    if not _bool(row, "basis_normalization_resolved"):
        failures.append("basis_normalization_unresolved")
    if str(row.get("runtime_complete_semantics", "")) != "explicit_harvested_cumulative_writeback_audited":
        failures.append("runtime_semantics_unresolved")
    dropped_mass = abs(_numeric(row, "dropped_nonharvested_mass_g_m2", default=0.0))
    if math.isfinite(dropped_mass) and dropped_mass > 1e-9:
        failures.append("dropped_nonharvested_mass")
    collapse_days = _numeric(row, "canopy_collapse_days")
    if math.isfinite(collapse_days) and collapse_days > 0.0:
        failures.append("canopy_collapse_days")
    return failures


def _metric_columns() -> list[str]:
    return [
        "rmse_cumulative_offset",
        "r2_cumulative_offset",
        "rmse_daily_increment",
        "fruit_anchor_error",
        "canopy_collapse_days",
        "native_state_coverage",
        "shared_tdvs_proxy_fraction",
        "mean_proxy_family_state_fraction",
    ]


def _score_rows(scorecard_df: pd.DataFrame) -> list[dict[str, object]]:
    if scorecard_df.empty:
        return []
    rows: list[dict[str, object]] = []
    for _, row in scorecard_df.sort_values(["dataset_id", "allocation_lane_id"]).iterrows():
        payload: dict[str, object] = {
            "dataset_id": row.get("dataset_id"),
            "dataset_role": row.get("dataset_role"),
            "evidence_grade": row.get("evidence_grade"),
            "decision_weight": row.get("decision_weight"),
            "architecture_code": architecture_code(str(row.get("allocation_lane_id", ""))),
            "architecture_id": architecture_family_id(str(row.get("allocation_lane_id", ""))),
            "repo_lane_alias": row.get("allocation_lane_id"),
            "harvest_profile_id": row.get("harvest_profile_id"),
            "execution_status": row.get("execution_status"),
            "state_reconstruction_status": row.get("state_reconstruction_status"),
            "state_reconstruction_error": row.get("state_reconstruction_error"),
            "physiological_guardrail_failures": _guardrail_failures(row),
        }
        for column in _metric_columns():
            payload[column] = _json_ready(row.get(column))
        rows.append({key: _json_ready(value) for key, value in payload.items()})
    return rows


def _winner_by_dataset(scorecard_df: pd.DataFrame) -> list[dict[str, object]]:
    if scorecard_df.empty:
        return []
    work = scorecard_df.copy()
    work["rmse_cumulative_offset"] = pd.to_numeric(work["rmse_cumulative_offset"], errors="coerce")
    work["rmse_daily_increment"] = pd.to_numeric(work["rmse_daily_increment"], errors="coerce")
    work = work.loc[work["rmse_cumulative_offset"].notna()].copy()
    if work.empty:
        return []
    winners = (
        work.sort_values(["dataset_id", "rmse_cumulative_offset", "rmse_daily_increment", "allocation_lane_id"])
        .groupby("dataset_id", as_index=False)
        .first()
    )
    return _score_rows(winners)


def _winner_by_mean_rmse(scorecard_df: pd.DataFrame) -> dict[str, object]:
    if scorecard_df.empty:
        return {}
    work = scorecard_df.copy()
    work["rmse_cumulative_offset"] = pd.to_numeric(work["rmse_cumulative_offset"], errors="coerce")
    work["rmse_daily_increment"] = pd.to_numeric(work["rmse_daily_increment"], errors="coerce")
    work = work.loc[work["rmse_cumulative_offset"].notna()].copy()
    if work.empty:
        return {}
    summary = (
        work.groupby("allocation_lane_id", as_index=False)
        .agg(
            mean_rmse_cumulative_offset=("rmse_cumulative_offset", "mean"),
            mean_rmse_daily_increment=("rmse_daily_increment", "mean"),
            dataset_count=("dataset_id", "nunique"),
        )
        .sort_values(["mean_rmse_cumulative_offset", "mean_rmse_daily_increment", "allocation_lane_id"])
    )
    row = summary.iloc[0]
    tied = summary.loc[
        summary["mean_rmse_cumulative_offset"].sub(float(row["mean_rmse_cumulative_offset"])).abs() <= 1e-9
    ].copy()
    return {
        "architecture_code": architecture_code(str(row["allocation_lane_id"])),
        "architecture_id": architecture_family_id(str(row["allocation_lane_id"])),
        "repo_lane_alias": str(row["allocation_lane_id"]),
        "mean_rmse_cumulative_offset": _json_ready(float(row["mean_rmse_cumulative_offset"])),
        "mean_rmse_daily_increment": _json_ready(float(row["mean_rmse_daily_increment"])),
        "dataset_count": int(row["dataset_count"]),
        "tie_detected": int(tied.shape[0]) > 1,
        "tied_repo_lane_aliases": sorted(str(value) for value in tied["allocation_lane_id"]),
    }


def _score_payload(
    *,
    score_name: str,
    purpose: str,
    scorecard_df: pd.DataFrame,
    promotion_use: str,
) -> dict[str, object]:
    return {
        "score_name": score_name,
        "purpose": purpose,
        "promotion_use": promotion_use,
        "dataset_ids": sorted({str(value) for value in scorecard_df.get("dataset_id", [])}),
        "dataset_count": int(scorecard_df["dataset_id"].nunique()) if "dataset_id" in scorecard_df else 0,
        "architecture_scores": _score_rows(scorecard_df),
        "winner_by_dataset": _winner_by_dataset(scorecard_df),
        "winner_by_mean_rmse": _winner_by_mean_rmse(scorecard_df),
    }


def _architecture_matrix(allocation_lanes: list[ResolvedAllocationLane]) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "architecture_code": architecture_code(lane.lane_id),
                "architecture_id": architecture_family_id(lane.lane_id),
                "repo_lane_alias": lane.lane_id,
                "repo_architecture_id": lane.architecture_id,
                "candidate_label": lane.candidate_label,
                "partition_policy": lane.partition_policy,
                "promotion_eligible_in_code": bool(lane.promotion_eligible),
                "reference_only": bool(lane.reference_only),
                "diagnostic_only": bool(lane.diagnostic_only),
                "production_default_changed": False,
            }
            for lane in allocation_lanes
        ]
    )


def _dataset_role_matrix(dataset_roles: list[ResolvedDatasetRole]) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "dataset_id": dataset.dataset_id,
                "dataset_kind": dataset.dataset_kind,
                "display_name": dataset.display_name,
                "dataset_role": dataset.dataset_role,
                "evidence_grade": dataset.evidence_grade,
                "decision_weight": dataset.decision_weight,
                "proxy_caveat": dataset.proxy_caveat,
                "promotion_denominator_eligible": bool(dataset.promotion_denominator_eligible),
                "scorecard_included": bool(dataset.scorecard_included),
                "has_measured_harvest_contract": bool(dataset.has_measured_harvest_contract),
                "reporting_basis": dataset.reporting_basis,
                "plants_per_m2": dataset.plants_per_m2,
                "review_flags": ";".join(dataset.review_flags),
                "is_direct_dry_weight": dataset.is_direct_dry_weight,
                "observed_harvest_derivation": dataset.observed_harvest_derivation,
            }
            for dataset in dataset_roles
        ]
    )


def _per_dataset_metric_summary(scorecard_df: pd.DataFrame) -> pd.DataFrame:
    if scorecard_df.empty:
        return pd.DataFrame()
    rows: list[dict[str, object]] = []
    for _, row in scorecard_df.iterrows():
        payload = {
            "dataset_id": row.get("dataset_id"),
            "dataset_role": row.get("dataset_role"),
            "evidence_grade": row.get("evidence_grade"),
            "decision_weight": row.get("decision_weight"),
            "proxy_caveat": row.get("proxy_caveat"),
            "architecture_code": architecture_code(str(row.get("allocation_lane_id", ""))),
            "architecture_id": architecture_family_id(str(row.get("allocation_lane_id", ""))),
            "repo_lane_alias": row.get("allocation_lane_id"),
            "harvest_profile_id": row.get("harvest_profile_id"),
            "execution_status": row.get("execution_status"),
            "state_reconstruction_status": row.get("state_reconstruction_status"),
            "state_reconstruction_error": row.get("state_reconstruction_error"),
            "physiological_guardrail_failures": ";".join(_guardrail_failures(row)),
        }
        for column in _metric_columns():
            payload[column] = row.get(column)
        rows.append(payload)
    return pd.DataFrame(rows).sort_values(["dataset_id", "architecture_code", "harvest_profile_id"])


def write_lane_matrix_reproducibility_artifacts(
    *,
    paths: LaneMatrixArtifactPaths,
    allocation_lanes: list[ResolvedAllocationLane],
    dataset_roles: list[ResolvedDatasetRole],
    scorecard_df: pd.DataFrame,
) -> None:
    architecture_df = _architecture_matrix(allocation_lanes)
    dataset_role_df = _dataset_role_matrix(dataset_roles)
    metric_summary_df = _per_dataset_metric_summary(scorecard_df)

    architecture_df.to_csv(paths.architecture_matrix_path, index=False)
    dataset_role_df.to_csv(paths.dataset_role_matrix_path, index=False)
    metric_summary_df.to_csv(paths.per_dataset_metric_summary_path, index=False)

    direct_mask = _direct_measured_mask(scorecard_df)
    review_mask = _review_only_derived_dw_mask(scorecard_df)
    runnable_mask = _column_equals(scorecard_df, "dataset_role", "measured_harvest")

    write_json(
        paths.primary_measured_score_path,
        _json_tree(
            _score_payload(
                score_name="primary_measured_score",
                purpose="Direct measured-harvest promotion-gate evidence only.",
                scorecard_df=scorecard_df.loc[direct_mask].copy(),
                promotion_use="promotion_gate_only",
            )
        ),
    )
    write_json(
        paths.review_only_public_score_path,
        _json_tree(
            _score_payload(
                score_name="review_only_public_score",
                purpose="Review-only public derived-DW robustness and contradiction check.",
                scorecard_df=scorecard_df.loc[review_mask].copy(),
                promotion_use="not_allowed_for_promotion",
            )
        ),
    )
    write_json(
        paths.all_runnable_smoke_score_path,
        _json_tree(
            _score_payload(
                score_name="all_runnable_smoke_score",
                purpose="All runnable measured-harvest-compatible lanes for reproducibility smoke only.",
                scorecard_df=scorecard_df.loc[runnable_mask].copy(),
                promotion_use="smoke_only_not_a_pooled_promotion_score",
            )
        ),
    )
    paths.readme_path.write_text(
        "\n".join(
            [
                "# TOMICS A1-A4 multidataset lane matrix",
                "",
                "This output bundle compares A1-A4 TOMICS allocation lanes across the currently runnable ",
                "harvest-validation datasets.",
                "",
                "Datasets:",
                "- `knu_actual`: direct measured harvest, promotion-gate evidence.",
                "- `public_rda__yield`: review-only derived dry-weight lane, not promotion evidence.",
                "- `public_ai_competition__yield`: review-only derived dry-weight lane, not promotion evidence.",
                "",
                "Decision policy:",
                "- `primary_measured_score.json` uses only direct measured harvest evidence.",
                "- `review_only_public_score.json` keeps public derived-DW lanes separate.",
                "- `all_runnable_smoke_score.json` is a reproducibility smoke summary, not a promotion score.",
                "- A3 remains the shipped incumbent and A4 remains research-only in this follow-up.",
            ]
        )
        + "\n",
        encoding="utf-8",
    )


def write_promotion_gate_decision_artifact(
    *,
    paths: LaneMatrixArtifactPaths,
    scorecard_df: pd.DataFrame,
    decision_payload: dict[str, object],
) -> None:
    direct_mask = _direct_measured_mask(scorecard_df)
    review_mask = _review_only_derived_dw_mask(scorecard_df)
    payload: dict[str, object] = {
        "decision_scope": "multi_dataset_a1_a4_reproducibility_followup",
        "promotion_score_policy": "primary_measured_direct_harvest_only",
        "primary_measured_dataset_ids": sorted(
            {str(value) for value in scorecard_df.loc[direct_mask, "dataset_id"]}
        ),
        "review_only_dataset_ids": sorted({str(value) for value in scorecard_df.loc[review_mask, "dataset_id"]}),
        "a3_decision": "keep_shipped_incumbent",
        "a4_decision": "keep_research_only",
        "public_proxy_lanes_can_promote_a4": False,
        "lane_gate_decision": decision_payload,
    }
    write_json(paths.promotion_gate_decision_path, _json_tree(payload))


__all__ = [
    "ARCHITECTURE_CODE_BY_LANE",
    "ARCHITECTURE_FAMILY_BY_LANE",
    "architecture_code",
    "architecture_family_id",
    "write_lane_matrix_reproducibility_artifacts",
    "write_promotion_gate_decision_artifact",
]
