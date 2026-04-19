from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pandas as pd

if TYPE_CHECKING:
    from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.datasets.registry import DatasetRegistry


def _bool_series(frame: pd.DataFrame, column: str) -> pd.Series:
    if column not in frame.columns:
        return pd.Series(False, index=frame.index, dtype=bool)
    normalized = frame[column].fillna(False).astype(str).str.strip().str.lower()
    return normalized.isin({"true", "1", "yes"})


def _nonempty_series(frame: pd.DataFrame, column: str) -> pd.Series:
    if column not in frame.columns:
        return pd.Series(False, index=frame.index, dtype=bool)
    return frame[column].fillna("").astype(str).str.strip().ne("")


def _existing_path_series(frame: pd.DataFrame, column: str) -> pd.Series:
    if column not in frame.columns:
        return pd.Series(False, index=frame.index, dtype=bool)
    values = frame[column].fillna("").astype(str).str.strip()
    return values.apply(lambda value: bool(value) and Path(value).exists())


def _json_list(value: object) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value]
    if value is None:
        return []
    try:
        parsed = json.loads(str(value))
    except (TypeError, ValueError, json.JSONDecodeError):
        return []
    if isinstance(parsed, list):
        return [str(item) for item in parsed]
    return []


def _selected_candidate_review_proxy_dataset_ids(
    registry_df: pd.DataFrame | None,
    candidate: pd.Series,
) -> list[str]:
    if registry_df is None or registry_df.empty:
        return []
    selected_dataset_ids = set(_json_list(candidate.get("dataset_ids")))
    if not selected_dataset_ids:
        return []
    candidate_rows = registry_df.loc[registry_df["dataset_id"].astype(str).isin(selected_dataset_ids)].copy()
    if candidate_rows.empty:
        return []
    review_flag_mask = candidate_rows.get("review_flags", pd.Series(dtype=object)).apply(
        lambda value: "review_only_dry_matter_conversion" in _json_list(value)
    )
    derivation_mask = (
        candidate_rows.get("observed_harvest_derivation", pd.Series(dtype=object))
        .fillna("")
        .astype(str)
        .str.strip()
        .str.startswith("derived_dw_from_measured_fresh_")
    )
    direct_dw_mask = (
        candidate_rows.get("is_direct_dry_weight", pd.Series(dtype=object))
        .fillna(True)
        .astype(str)
        .str.strip()
        .str.lower()
        .isin({"true", "1", "yes"})
    )
    literature_ratio_mask = (
        candidate_rows.get("uses_literature_dry_matter_fraction", pd.Series(dtype=object))
        .fillna(False)
        .astype(str)
        .str.strip()
        .str.lower()
        .isin({"true", "1", "yes"})
    )
    flagged = candidate_rows.loc[
        review_flag_mask | (derivation_mask & (~direct_dw_mask) & literature_ratio_mask),
        "dataset_id",
    ]
    return sorted({str(value) for value in flagged.dropna()})


def _registry_measured_dataset_support(registry_df: pd.DataFrame | None) -> tuple[int, list[str]]:
    if registry_df is None or registry_df.empty:
        return 0, []
    capability = registry_df.get("capability", pd.Series(dtype=object)).astype(str).str.strip().str.lower()
    mask = (
        capability.eq("measured_harvest")
        & _bool_series(registry_df, "is_runnable_measured_harvest")
        & _bool_series(registry_df, "basis_normalization_resolved")
        & _nonempty_series(registry_df, "validation_start")
        & _nonempty_series(registry_df, "validation_end")
        & _nonempty_series(registry_df, "date_column")
        & _nonempty_series(registry_df, "measured_cumulative_column")
        & _existing_path_series(registry_df, "forcing_path")
        & _existing_path_series(registry_df, "observed_harvest_path")
        & _existing_path_series(registry_df, "sanitized_fixture_path")
    )
    dataset_ids = sorted({str(value) for value in registry_df.loc[mask, "dataset_id"].dropna()})
    return len(dataset_ids), dataset_ids


def cross_dataset_proxy_guardrail(
    candidate: pd.Series,
    *,
    native_state_coverage_min: float,
    shared_tdvs_proxy_fraction_max: float,
    cross_dataset_stability_score_min: float,
    min_dataset_count: int,
    measured_dataset_count: int | None = None,
    review_only_proxy_dataset_ids: list[str] | None = None,
) -> dict[str, Any]:
    native_state_coverage = float(
        pd.to_numeric(pd.Series([candidate.get("mean_native_family_state_fraction", 0.0)]), errors="coerce")
        .fillna(0.0)
        .iloc[0]
    )
    proxy_state_fraction = float(
        pd.to_numeric(pd.Series([candidate.get("mean_proxy_family_state_fraction", 0.0)]), errors="coerce")
        .fillna(0.0)
        .iloc[0]
    )
    shared_tdvs_proxy_fraction = float(
        pd.to_numeric(pd.Series([candidate.get("mean_shared_tdvs_proxy_fraction", 0.0)]), errors="coerce")
        .fillna(0.0)
        .iloc[0]
    )
    stability_score = float(
        pd.to_numeric(pd.Series([candidate.get("cross_dataset_stability_score", 0.0)]), errors="coerce")
        .fillna(0.0)
        .iloc[0]
    )
    selected_candidate_dataset_count = int(
        pd.to_numeric(pd.Series([candidate.get("dataset_count", 0)]), errors="coerce").fillna(0).iloc[0]
    )
    measured_dataset_evidence_available = measured_dataset_count is not None
    registry_measured_dataset_count = int(measured_dataset_count or 0)
    review_only_proxy_dataset_ids = sorted({str(value) for value in review_only_proxy_dataset_ids or []})
    review_only_proxy_support_flag = bool(review_only_proxy_dataset_ids)
    proxy_heavy_flag = bool(
        native_state_coverage < native_state_coverage_min
        or shared_tdvs_proxy_fraction > shared_tdvs_proxy_fraction_max
    )
    single_dataset_only_flag = (
        selected_candidate_dataset_count < int(min_dataset_count)
        or registry_measured_dataset_count < int(min_dataset_count)
    )
    stability_fail_flag = stability_score < cross_dataset_stability_score_min
    missing_dataset_registry_flag = not measured_dataset_evidence_available
    return {
        "winner_native_state_coverage": native_state_coverage,
        "winner_proxy_state_fraction": proxy_state_fraction,
        "winner_shared_tdvs_proxy_fraction": shared_tdvs_proxy_fraction,
        "winner_proxy_heavy_flag": proxy_heavy_flag,
        "winner_review_only_proxy_dataset_ids": review_only_proxy_dataset_ids,
        "winner_review_only_proxy_support_flag": review_only_proxy_support_flag,
        "cross_dataset_stability_score": stability_score,
        "measured_dataset_count": registry_measured_dataset_count,
        "measured_dataset_evidence_available": measured_dataset_evidence_available,
        "selected_candidate_dataset_count": selected_candidate_dataset_count,
        "single_dataset_only_flag": single_dataset_only_flag,
        "missing_dataset_registry_flag": missing_dataset_registry_flag,
        "winner_not_promotion_grade_due_to_proxy_dependence": proxy_heavy_flag,
        "winner_not_promotion_grade_due_to_review_only_proxy_support": review_only_proxy_support_flag,
        "winner_not_promotion_grade_due_to_cross_dataset_instability": (
            single_dataset_only_flag or stability_fail_flag or missing_dataset_registry_flag
        ),
        "passes": not (
            proxy_heavy_flag
            or review_only_proxy_support_flag
            or single_dataset_only_flag
            or stability_fail_flag
            or missing_dataset_registry_flag
        ),
    }


def build_cross_dataset_guardrail_summary(
    scorecard_df: pd.DataFrame,
    *,
    registry: "DatasetRegistry | None" = None,
    registry_df: pd.DataFrame | None = None,
    native_state_coverage_min: float = 0.5,
    shared_tdvs_proxy_fraction_max: float = 0.5,
    cross_dataset_stability_score_min: float = 0.5,
    min_dataset_count: int = 2,
) -> dict[str, Any]:
    if registry_df is None and registry is not None:
        registry_df = registry.to_frame()
    measured_dataset_count, measured_dataset_ids = _registry_measured_dataset_support(registry_df)
    registry_evidence_available = registry_df is not None and not registry_df.empty
    registry_summary = {}
    if registry_evidence_available:
        registry_summary = {
            "total_registry_datasets": int(registry_df.shape[0]),
            "proxy_dataset_count": int(
                registry_df.get("capability", pd.Series(dtype=object))
                .astype(str)
                .str.strip()
                .str.lower()
                .eq("harvest_proxy")
                .sum()
            ),
            "context_only_dataset_count": int(
                registry_df.get("capability", pd.Series(dtype=object))
                .astype(str)
                .str.strip()
                .str.lower()
                .eq("context_only")
                .sum()
            ),
            "draft_dataset_count": int(
                registry_df.get("ingestion_status", pd.Series(dtype=object))
                .astype(str)
                .str.strip()
                .str.lower()
                .ne("runnable")
                .sum()
            ),
            "measured_dataset_evidence_available": True,
        }
    else:
        registry_summary = {"measured_dataset_evidence_available": False}
    guardrails = {
        "winner_native_state_coverage_min": native_state_coverage_min,
        "winner_shared_tdvs_proxy_fraction_max": shared_tdvs_proxy_fraction_max,
        "cross_dataset_stability_score_min": cross_dataset_stability_score_min,
        "min_dataset_count": min_dataset_count,
    }
    if scorecard_df.empty:
        return {
            "recommendation": (
                "Promotion remains blocked by design until at least two runnable measured-harvest datasets are registered."
                if measured_dataset_count < int(min_dataset_count)
                else "Promotion remains blocked because no cross-dataset factorial winner is available yet."
            ),
            "guardrails": guardrails,
            "dataset_inventory_summary": registry_summary,
            "measured_dataset_count": measured_dataset_count,
            "measured_dataset_ids": measured_dataset_ids,
            "selected_candidate": {},
        }
    selected = scorecard_df.iloc[0]
    review_only_proxy_dataset_ids = _selected_candidate_review_proxy_dataset_ids(registry_df, selected)
    guardrail = cross_dataset_proxy_guardrail(
        selected,
        native_state_coverage_min=native_state_coverage_min,
        shared_tdvs_proxy_fraction_max=shared_tdvs_proxy_fraction_max,
        cross_dataset_stability_score_min=cross_dataset_stability_score_min,
        min_dataset_count=min_dataset_count,
        measured_dataset_count=measured_dataset_count if registry_evidence_available else None,
        review_only_proxy_dataset_ids=review_only_proxy_dataset_ids,
    )
    if not registry_evidence_available:
        recommendation = (
            "Promotion remains blocked until runnable measured-harvest dataset support is resolved from the dataset registry."
        )
    elif not guardrail["passes"]:
        recommendation = "Promotion remains blocked until a winner holds across multiple runnable measured-harvest datasets."
    else:
        recommendation = "Promotion-grade cross-dataset winner available."
    return {
        "recommendation": recommendation,
        "guardrails": guardrails,
        "dataset_inventory_summary": registry_summary,
        "measured_dataset_count": measured_dataset_count,
        "measured_dataset_ids": measured_dataset_ids,
        "selected_candidate": {**selected.to_dict(), **guardrail},
    }


__all__ = ["build_cross_dataset_guardrail_summary", "cross_dataset_proxy_guardrail"]
