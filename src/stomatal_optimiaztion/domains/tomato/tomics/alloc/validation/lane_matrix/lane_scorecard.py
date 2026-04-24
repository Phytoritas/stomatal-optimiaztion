from __future__ import annotations

import math

import pandas as pd

from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.harvest_mass_balance_eval import (
    winner_stability_score,
)
from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.observation_model import (
    compute_validation_bundle,
)
from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.parameter_budget import (
    build_split_windows,
)
from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.lane_matrix.scenario import (
    ComparisonScenario,
)


RUNTIME_COMPLETE_SEMANTICS = "explicit_harvested_cumulative_writeback_audited"
RUNTIME_UNRESOLVED = "unresolved"


def _all_zero_series(frame: pd.DataFrame, column: str) -> bool:
    if column not in frame.columns or frame.empty:
        return True
    series = pd.to_numeric(frame[column], errors="coerce").fillna(0.0)
    return bool((series.abs() <= 1e-12).all())


def _harvest_series_diagnostics(validation_df: pd.DataFrame) -> dict[str, bool]:
    zero_increment = _all_zero_series(validation_df, "model_daily_increment_floor_area")
    zero_cumulative = _all_zero_series(
        validation_df,
        "model_cumulative_harvested_fruit_dry_weight_floor_area",
    )
    return {
        "all_zero_model_daily_increment_series": zero_increment,
        "all_zero_model_cumulative_harvest_series": zero_cumulative,
        "any_all_zero_harvest_series": bool(zero_increment and zero_cumulative),
    }


def _runtime_complete(validation_df: pd.DataFrame, metrics: dict[str, object]) -> str:
    required_columns = {
        "model_cumulative_harvested_fruit_dry_weight_floor_area",
        "model_daily_increment_floor_area",
        "measured_cumulative_total_fruit_dry_weight_floor_area",
        "measured_daily_increment_floor_area",
    }
    required_metrics = {
        "post_writeback_dropped_nonharvested_mass_g_m2",
        "offplant_with_positive_mass_flag",
        "native_family_state_fraction",
        "shared_tdvs_proxy_fraction",
    }
    if required_columns.issubset(validation_df.columns) and required_metrics.issubset(metrics):
        return RUNTIME_COMPLETE_SEMANTICS
    return RUNTIME_UNRESOLVED


def build_context_only_lane_scorecard_row(
    scenario: ComparisonScenario,
    *,
    execution_status: str,
    basis_normalization_resolved: bool | None = None,
) -> dict[str, object]:
    dataset_assignment = scenario.dataset_role_assignment
    resolved_basis = (
        bool(basis_normalization_resolved)
        if basis_normalization_resolved is not None
        else dataset_assignment.reporting_basis == "floor_area_g_m2"
    )
    return {
        "scenario_id": scenario.scenario_id,
        "allocation_lane_id": scenario.allocation_lane.lane_id,
        "harvest_profile_id": scenario.harvest_profile.harvest_profile_id,
        "dataset_id": dataset_assignment.dataset_id,
        "dataset_role": dataset_assignment.dataset_role,
        "evidence_grade": dataset_assignment.evidence_grade,
        "decision_weight": dataset_assignment.decision_weight,
        "proxy_caveat": dataset_assignment.proxy_caveat,
        "review_flags": ";".join(dataset_assignment.review_flags),
        "is_direct_dry_weight": dataset_assignment.is_direct_dry_weight,
        "observed_harvest_derivation": dataset_assignment.observed_harvest_derivation,
        "promotion_eligible": bool(scenario.promotion_surface_eligible),
        "reference_only": bool(scenario.allocation_lane.reference_only),
        "reporting_basis_in": dataset_assignment.reporting_basis,
        "reporting_basis_canonical": "floor_area_g_m2",
        "basis_normalization_resolved": bool(resolved_basis),
        "rmse_cumulative_offset": math.nan,
        "r2_cumulative_offset": math.nan,
        "rmse_daily_increment": math.nan,
        "fruit_anchor_error": math.nan,
        "canopy_collapse_days": math.nan,
        "winner_stability_score": math.nan,
        "native_state_coverage": math.nan,
        "shared_tdvs_proxy_fraction": math.nan,
        "family_separability_score": math.nan,
        "any_all_zero_harvest_series": False,
        "all_zero_model_daily_increment_series": False,
        "all_zero_model_cumulative_harvest_series": False,
        "dropped_nonharvested_mass_g_m2": 0.0,
        "offplant_with_positive_mass_flag": False,
        "runtime_complete_semantics": RUNTIME_UNRESOLVED,
        "selected_family_label": scenario.harvest_profile.selected_family_label,
        "selected_family_is_native": bool(scenario.harvest_profile.selected_family_is_native),
        "selected_family_is_proxy": bool(scenario.harvest_profile.selected_family_is_proxy),
        "execution_status": execution_status,
        "state_reconstruction_status": "not_attempted",
        "state_reconstruction_error": "",
        "candidate_label": scenario.allocation_lane.candidate_label,
        "architecture_id": scenario.allocation_lane.architecture_id,
        "partition_policy": scenario.allocation_lane.partition_policy,
        "mean_alloc_frac_fruit": math.nan,
        "mean_proxy_family_state_fraction": math.nan,
    }


def build_lane_scorecard_row(
    scenario: ComparisonScenario,
    *,
    validation_df: pd.DataFrame,
    run_df: pd.DataFrame,
    metrics: dict[str, object],
    basis_normalization_resolved: bool | None = None,
) -> dict[str, object]:
    dataset_assignment = scenario.dataset_role_assignment
    reporting_basis_in = dataset_assignment.reporting_basis
    resolved_basis = (
        bool(basis_normalization_resolved)
        if basis_normalization_resolved is not None
        else reporting_basis_in == "floor_area_g_m2"
    )
    native_state_coverage = float(metrics.get("native_family_state_fraction", 0.0))
    shared_tdvs_proxy_fraction = float(metrics.get("shared_tdvs_proxy_fraction", 0.0))
    proxy_fraction = float(metrics.get("proxy_family_state_fraction", 0.0))
    harvest_series = _harvest_series_diagnostics(validation_df)
    return {
        "scenario_id": scenario.scenario_id,
        "allocation_lane_id": scenario.allocation_lane.lane_id,
        "harvest_profile_id": scenario.harvest_profile.harvest_profile_id,
        "dataset_id": dataset_assignment.dataset_id,
        "dataset_role": dataset_assignment.dataset_role,
        "evidence_grade": dataset_assignment.evidence_grade,
        "decision_weight": dataset_assignment.decision_weight,
        "proxy_caveat": dataset_assignment.proxy_caveat,
        "review_flags": ";".join(dataset_assignment.review_flags),
        "is_direct_dry_weight": dataset_assignment.is_direct_dry_weight,
        "observed_harvest_derivation": dataset_assignment.observed_harvest_derivation,
        "promotion_eligible": bool(scenario.promotion_surface_eligible),
        "reference_only": bool(scenario.allocation_lane.reference_only),
        "reporting_basis_in": reporting_basis_in,
        "reporting_basis_canonical": "floor_area_g_m2",
        "basis_normalization_resolved": bool(resolved_basis),
        "rmse_cumulative_offset": float(metrics.get("rmse_cumulative_offset", math.nan)),
        "r2_cumulative_offset": float(metrics.get("r2_cumulative_offset", math.nan)),
        "rmse_daily_increment": float(metrics.get("rmse_daily_increment", math.nan)),
        "fruit_anchor_error": math.nan,
        "canopy_collapse_days": float(metrics.get("canopy_collapse_days", math.nan)),
        "winner_stability_score": math.nan,
        "native_state_coverage": native_state_coverage,
        "shared_tdvs_proxy_fraction": shared_tdvs_proxy_fraction,
        "family_separability_score": max(native_state_coverage - shared_tdvs_proxy_fraction, 0.0),
        **harvest_series,
        "dropped_nonharvested_mass_g_m2": float(metrics.get("post_writeback_dropped_nonharvested_mass_g_m2", 0.0)),
        "offplant_with_positive_mass_flag": bool(metrics.get("offplant_with_positive_mass_flag", False)),
        "runtime_complete_semantics": _runtime_complete(validation_df, metrics),
        "selected_family_label": scenario.harvest_profile.selected_family_label,
        "selected_family_is_native": bool(scenario.harvest_profile.selected_family_is_native),
        "selected_family_is_proxy": bool(scenario.harvest_profile.selected_family_is_proxy),
        "execution_status": "scored",
        "state_reconstruction_status": str(metrics.get("state_reconstruction_status", "reconstructed")),
        "state_reconstruction_error": str(metrics.get("state_reconstruction_error", "")),
        "candidate_label": scenario.allocation_lane.candidate_label,
        "architecture_id": scenario.allocation_lane.architecture_id,
        "partition_policy": scenario.allocation_lane.partition_policy,
        "mean_alloc_frac_fruit": float(
            pd.to_numeric(run_df.get("alloc_frac_fruit"), errors="coerce").dropna().mean()
        )
        if "alloc_frac_fruit" in run_df.columns
        else math.nan,
        "mean_proxy_family_state_fraction": proxy_fraction,
    }


def build_diagnostic_runtime_lane_scorecard_row(
    scenario: ComparisonScenario,
    *,
    validation_df: pd.DataFrame,
    run_df: pd.DataFrame,
    metrics: dict[str, object],
    basis_normalization_resolved: bool | None = None,
) -> dict[str, object]:
    row = build_lane_scorecard_row(
        scenario,
        validation_df=validation_df,
        run_df=run_df,
        metrics=metrics,
        basis_normalization_resolved=basis_normalization_resolved,
    )
    row["execution_status"] = "diagnostic_runtime_scored"
    row["rmse_cumulative_offset"] = math.nan
    row["rmse_daily_increment"] = math.nan
    row["winner_stability_score"] = math.nan
    return row


def build_split_score_rows(
    scenario: ComparisonScenario,
    *,
    observed_df: pd.DataFrame,
    validation_df: pd.DataFrame,
) -> list[dict[str, object]]:
    split_rows: list[dict[str, object]] = []
    try:
        split_windows = build_split_windows(observed_df)
    except ValueError:
        return split_rows
    for split in split_windows:
        dates = pd.to_datetime(validation_df["date"], errors="coerce").dt.normalize()
        mask = (dates >= split.calibration_start) & (dates <= split.holdout_end)
        window = validation_df.loc[mask].copy()
        if window.empty:
            continue
        bundle = compute_validation_bundle(
            window[
                [
                    "date",
                    "measured_cumulative_total_fruit_dry_weight_floor_area",
                    "measured_daily_increment_floor_area",
                ]
            ].copy(),
            candidate_series=window["model_cumulative_harvested_fruit_dry_weight_floor_area"],
            candidate_daily_increment_series=window["model_daily_increment_floor_area"],
            candidate_label="model",
            unit_declared_in_observation_file="g/m^2",
        )
        metrics = bundle.metrics
        split_rows.append(
            {
                "scenario_id": scenario.scenario_id,
                "dataset_id": scenario.dataset_role_assignment.dataset_id,
                "harvest_profile_id": scenario.harvest_profile.harvest_profile_id,
                "allocation_lane_id": scenario.allocation_lane.lane_id,
                "split_label": split.split_id,
                "score": float(
                    -float(metrics.get("rmse_cumulative_offset", math.inf))
                    - 0.5 * float(metrics.get("rmse_daily_increment", math.inf))
                ),
            }
        )
    return split_rows


def finalize_lane_scorecard(
    scorecard_df: pd.DataFrame,
    *,
    split_score_df: pd.DataFrame,
) -> pd.DataFrame:
    if scorecard_df.empty:
        return scorecard_df
    finalized = scorecard_df.copy()
    finalized["fruit_anchor_error"] = pd.to_numeric(finalized["fruit_anchor_error"], errors="coerce")
    for (dataset_id, harvest_profile_id), group in finalized.groupby(["dataset_id", "harvest_profile_id"]):
        incumbent_rows = group.loc[group["allocation_lane_id"].eq("incumbent_current")]
        if incumbent_rows.empty:
            continue
        incumbent_mean = float(pd.to_numeric(incumbent_rows["mean_alloc_frac_fruit"], errors="coerce").dropna().mean())
        mask = finalized["dataset_id"].eq(dataset_id) & finalized["harvest_profile_id"].eq(harvest_profile_id)
        finalized.loc[mask, "fruit_anchor_error"] = (
            pd.to_numeric(finalized.loc[mask, "mean_alloc_frac_fruit"], errors="coerce") - incumbent_mean
        ).abs()
    if not split_score_df.empty:
        keyed_rows: list[pd.DataFrame] = []
        for (dataset_id, harvest_profile_id), group in split_score_df.groupby(["dataset_id", "harvest_profile_id"]):
            row = winner_stability_score(group, candidate_column="allocation_lane_id")
            row["dataset_id"] = dataset_id
            row["harvest_profile_id"] = harvest_profile_id
            keyed_rows.append(row)
        if keyed_rows:
            stability_df = pd.concat(keyed_rows, ignore_index=True)
            finalized = finalized.merge(
                stability_df[["dataset_id", "harvest_profile_id", "allocation_lane_id", "winner_stability_score"]],
                on=["dataset_id", "harvest_profile_id", "allocation_lane_id"],
                how="left",
                suffixes=("", "_stability"),
            )
            if "winner_stability_score_stability" in finalized.columns:
                finalized["winner_stability_score"] = finalized["winner_stability_score_stability"].combine_first(
                    finalized["winner_stability_score"]
                )
                finalized = finalized.drop(columns=["winner_stability_score_stability"])
    finalized["winner_stability_score"] = pd.to_numeric(
        finalized["winner_stability_score"],
        errors="coerce",
    )
    return finalized


def promotion_audit_passes(row: pd.Series) -> bool:
    dropped_mass = float(
        pd.to_numeric(pd.Series([row.get("dropped_nonharvested_mass_g_m2", math.inf)]), errors="coerce")
        .fillna(math.inf)
        .iloc[0]
    )
    return bool(
        not bool(row.get("any_all_zero_harvest_series", False))
        and abs(dropped_mass) <= 1e-9
        and not bool(row.get("offplant_with_positive_mass_flag", False))
        and str(row.get("runtime_complete_semantics", "")) == RUNTIME_COMPLETE_SEMANTICS
        and bool(row.get("basis_normalization_resolved", False))
    )


__all__ = [
    "RUNTIME_COMPLETE_SEMANTICS",
    "RUNTIME_UNRESOLVED",
    "build_context_only_lane_scorecard_row",
    "build_diagnostic_runtime_lane_scorecard_row",
    "build_lane_scorecard_row",
    "build_split_score_rows",
    "finalize_lane_scorecard",
    "promotion_audit_passes",
]
