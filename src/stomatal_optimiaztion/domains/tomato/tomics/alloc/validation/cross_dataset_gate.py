from __future__ import annotations

from typing import Any

import pandas as pd


def cross_dataset_proxy_guardrail(
    candidate: pd.Series,
    *,
    native_state_coverage_min: float,
    shared_tdvs_proxy_fraction_max: float,
    cross_dataset_stability_score_min: float,
    min_dataset_count: int,
) -> dict[str, float | bool]:
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
    dataset_count = int(pd.to_numeric(pd.Series([candidate.get("dataset_count", 0)]), errors="coerce").fillna(0).iloc[0])
    proxy_heavy_flag = bool(
        native_state_coverage < native_state_coverage_min
        or shared_tdvs_proxy_fraction > shared_tdvs_proxy_fraction_max
    )
    single_dataset_only_flag = dataset_count < int(min_dataset_count)
    stability_fail_flag = stability_score < cross_dataset_stability_score_min
    return {
        "winner_native_state_coverage": native_state_coverage,
        "winner_proxy_state_fraction": proxy_state_fraction,
        "winner_shared_tdvs_proxy_fraction": shared_tdvs_proxy_fraction,
        "winner_proxy_heavy_flag": proxy_heavy_flag,
        "cross_dataset_stability_score": stability_score,
        "single_dataset_only_flag": single_dataset_only_flag,
        "winner_not_promotion_grade_due_to_proxy_dependence": proxy_heavy_flag,
        "winner_not_promotion_grade_due_to_cross_dataset_instability": single_dataset_only_flag or stability_fail_flag,
        "passes": not (proxy_heavy_flag or single_dataset_only_flag or stability_fail_flag),
    }


def build_cross_dataset_guardrail_summary(
    scorecard_df: pd.DataFrame,
    *,
    native_state_coverage_min: float = 0.5,
    shared_tdvs_proxy_fraction_max: float = 0.5,
    cross_dataset_stability_score_min: float = 0.5,
    min_dataset_count: int = 2,
) -> dict[str, Any]:
    if scorecard_df.empty:
        return {
            "recommendation": "No registered datasets were available for cross-dataset promotion.",
            "guardrails": {
                "winner_native_state_coverage_min": native_state_coverage_min,
                "winner_shared_tdvs_proxy_fraction_max": shared_tdvs_proxy_fraction_max,
                "cross_dataset_stability_score_min": cross_dataset_stability_score_min,
                "min_dataset_count": min_dataset_count,
            },
            "selected_candidate": {},
        }
    selected = scorecard_df.iloc[0]
    guardrail = cross_dataset_proxy_guardrail(
        selected,
        native_state_coverage_min=native_state_coverage_min,
        shared_tdvs_proxy_fraction_max=shared_tdvs_proxy_fraction_max,
        cross_dataset_stability_score_min=cross_dataset_stability_score_min,
        min_dataset_count=min_dataset_count,
    )
    recommendation = (
        "Promotion remains blocked until a winner holds across multiple measured datasets."
        if not guardrail["passes"]
        else "Promotion-grade cross-dataset winner available."
    )
    return {
        "recommendation": recommendation,
        "guardrails": {
            "winner_native_state_coverage_min": native_state_coverage_min,
            "winner_shared_tdvs_proxy_fraction_max": shared_tdvs_proxy_fraction_max,
            "cross_dataset_stability_score_min": cross_dataset_stability_score_min,
            "min_dataset_count": min_dataset_count,
        },
        "selected_candidate": {**selected.to_dict(), **guardrail},
    }


__all__ = ["build_cross_dataset_guardrail_summary", "cross_dataset_proxy_guardrail"]
