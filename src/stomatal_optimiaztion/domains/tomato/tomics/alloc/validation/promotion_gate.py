from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from stomatal_optimiaztion.domains.tomato.tomics.alloc.core import ensure_dir, write_json
from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.calibration import (
    _as_dict,
    _resolve_config_path,
)
from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.observation_model import (
    validation_overlay_frame,
)


def _aggregate_candidate(frame: pd.DataFrame) -> dict[str, object]:
    return {
        "architecture_id": str(frame["architecture_id"].iloc[0]),
        "mean_holdout_rmse_cumulative_offset": float(pd.to_numeric(frame["holdout_rmse_cumulative_offset"], errors="coerce").mean()),
        "mean_holdout_mae_cumulative_offset": float(pd.to_numeric(frame["holdout_mae_cumulative_offset"], errors="coerce").mean()),
        "mean_holdout_r2_cumulative_offset": float(pd.to_numeric(frame["holdout_r2_cumulative_offset"], errors="coerce").mean()),
        "mean_holdout_rmse_daily_increment": float(pd.to_numeric(frame["holdout_rmse_daily_increment"], errors="coerce").mean()),
        "mean_holdout_mae_daily_increment": float(pd.to_numeric(frame["holdout_mae_daily_increment"], errors="coerce").mean()),
        "mean_holdout_final_bias": float(pd.to_numeric(frame["holdout_final_bias"], errors="coerce").mean()),
        "max_fruit_anchor_error_vs_legacy": float(pd.to_numeric(frame["fruit_anchor_error_vs_legacy"], errors="coerce").fillna(0.0).max()),
        "max_canopy_collapse_days": float(pd.to_numeric(frame["canopy_collapse_days"], errors="coerce").fillna(0.0).max()),
        "max_wet_condition_root_excess_penalty": float(pd.to_numeric(frame["wet_condition_root_excess_penalty"], errors="coerce").fillna(0.0).max()),
        "max_parameter_instability_score": float(pd.to_numeric(frame["parameter_instability_score"], errors="coerce").fillna(0.0).max()),
    }


def _render_promotion_overlay(*, output_root: Path, scorecard_df: pd.DataFrame, holdout_results: pd.DataFrame, spec_path: Path) -> None:
    from stomatal_optimiaztion.domains.tomato.tomics.plotting import render_partition_compare_bundle

    blocked = holdout_results[
        holdout_results["split_label"].eq("blocked_holdout")
        & holdout_results["candidate_label"].isin(scorecard_df["candidate_label"])
    ].copy()
    runs: dict[str, pd.DataFrame] = {}
    for _, row in blocked.iterrows():
        frame = pd.read_csv(row["validation_series_csv"])
        runs[str(row["candidate_label"])] = validation_overlay_frame(
            frame,
            source_label=str(row["candidate_label"]),
        )
    if runs:
        render_partition_compare_bundle(
            runs=runs,
            out_path=output_root / "promotion_holdout_overlay.png",
            spec_path=spec_path,
        )


def run_promotion_gate(
    config: dict[str, Any],
    *,
    repo_root: Path,
    config_path: Path,
) -> dict[str, object]:
    gate_cfg = _as_dict(config.get("promotion_gate"))
    calibration_cfg = _as_dict(config.get("calibration"))
    calibration_root = _resolve_config_path(
        calibration_cfg.get("output_root", "out/tomics_knu_calibration"),
        repo_root=repo_root,
        config_path=config_path,
    )
    output_root = ensure_dir(
        _resolve_config_path(
            gate_cfg.get("output_root", "out/tomics_knu_promotion_gate"),
            repo_root=repo_root,
            config_path=config_path,
        )
    )
    holdout_results = pd.read_csv(calibration_root / "holdout_results.csv")
    winner_stability = pd.read_csv(calibration_root / "winner_stability.csv")
    parameter_stability = pd.read_csv(calibration_root / "parameter_stability.csv")

    promotion_candidates = ["shipped_tomics", "current_selected", "promoted_selected"]
    comparator_candidates = ["workbook_estimated"]
    score_rows: list[dict[str, object]] = []
    for candidate_label in [*comparator_candidates, *promotion_candidates]:
        frame = holdout_results[holdout_results["candidate_label"].eq(candidate_label)].copy()
        if frame.empty:
            continue
        row = {"candidate_label": candidate_label, **_aggregate_candidate(frame)}
        stability = winner_stability[winner_stability["candidate_label"].eq(candidate_label)]
        row["win_fraction"] = float(pd.to_numeric(stability["win_fraction"], errors="coerce").iloc[0]) if not stability.empty else 0.0
        score_rows.append(row)
    scorecard_df = pd.DataFrame(score_rows)
    scorecard_df.to_csv(output_root / "promotion_scorecard.csv", index=False)
    winner_stability.to_csv(output_root / "winner_stability.csv", index=False)

    shipped = scorecard_df[scorecard_df["candidate_label"].eq("shipped_tomics")].iloc[0]
    current = scorecard_df[scorecard_df["candidate_label"].eq("current_selected")].iloc[0]
    promoted = scorecard_df[scorecard_df["candidate_label"].eq("promoted_selected")].iloc[0]

    rmse_margin = float(gate_cfg.get("material_rmse_margin", 1.0))
    rmse_fraction = float(gate_cfg.get("material_rmse_fraction", 0.05))
    guardrails = {
        "fruit_anchor_error_vs_legacy_max": 0.03,
        "canopy_collapse_days_max": 0.0,
        "wet_condition_root_excess_penalty_max": float(gate_cfg.get("wet_root_penalty_max", 0.02)),
        "parameter_instability_score_max": float(gate_cfg.get("parameter_instability_score_max", 0.20)),
        "material_rmse_margin": rmse_margin,
        "material_rmse_fraction": rmse_fraction,
    }
    def _material_improvement(candidate_row: pd.Series) -> bool:
        shipped_rmse = float(shipped["mean_holdout_rmse_cumulative_offset"])
        candidate_rmse = float(candidate_row["mean_holdout_rmse_cumulative_offset"])
        return (
            shipped_rmse - candidate_rmse >= rmse_margin
            and candidate_rmse <= shipped_rmse * (1.0 - rmse_fraction)
        )

    material_improvement = _material_improvement(promoted)
    promoted_passes = (
        material_improvement
        and float(promoted["max_fruit_anchor_error_vs_legacy"]) <= guardrails["fruit_anchor_error_vs_legacy_max"]
        and float(promoted["max_canopy_collapse_days"]) <= guardrails["canopy_collapse_days_max"]
        and float(promoted["max_wet_condition_root_excess_penalty"]) <= guardrails["wet_condition_root_excess_penalty_max"]
        and float(promoted["max_parameter_instability_score"]) <= guardrails["parameter_instability_score_max"]
        and float(promoted["win_fraction"]) >= 0.5
    )
    current_passes = (
        _material_improvement(current)
        and float(current["max_fruit_anchor_error_vs_legacy"]) <= guardrails["fruit_anchor_error_vs_legacy_max"]
        and float(current["max_canopy_collapse_days"]) <= guardrails["canopy_collapse_days_max"]
        and float(current["max_wet_condition_root_excess_penalty"]) <= guardrails["wet_condition_root_excess_penalty_max"]
        and float(current["max_parameter_instability_score"]) <= guardrails["parameter_instability_score_max"]
        and float(current["win_fraction"]) >= 0.5
    )
    incumbent = "shipped_tomics"
    recommendation = "keep shipped TOMICS incumbent"
    if promoted_passes:
        incumbent = "promoted_selected"
        recommendation = "promote promoted research allocator as next shipped-default candidate"
    elif current_passes:
        incumbent = "current_selected"
        recommendation = "promote current research allocator as next shipped-default candidate"

    guardrail_payload = {
        "guardrails": guardrails,
        "current_selected": {
            "passes": current_passes,
            "metrics": current.to_dict(),
        },
        "promoted_selected": {
            "passes": promoted_passes,
            "metrics": promoted.to_dict(),
        },
        "incumbent": incumbent,
        "promotion_allowed": incumbent != "shipped_tomics",
        "parameter_stability_rows": int(parameter_stability.shape[0]),
    }
    write_json(output_root / "promotion_guardrails.json", guardrail_payload)

    decision_md = "\n".join(
        [
            "# TOMICS KNU Promotion Gate",
            "",
            f"Recommendation: `{recommendation}`",
            f"Incumbent after fair validation: `{incumbent}`",
            "",
            "Decision basis:",
            f"- shipped TOMICS mean holdout RMSE offset-adjusted: {float(shipped['mean_holdout_rmse_cumulative_offset']):.4f}",
            f"- current selected mean holdout RMSE offset-adjusted: {float(current['mean_holdout_rmse_cumulative_offset']):.4f}",
            f"- promoted selected mean holdout RMSE offset-adjusted: {float(promoted['mean_holdout_rmse_cumulative_offset']):.4f}",
            f"- current selected win fraction: {float(current['win_fraction']):.2f}",
            f"- promoted selected win fraction: {float(promoted['win_fraction']):.2f}",
            "",
            "No research allocator is promoted unless it materially beats shipped TOMICS on holdout fit and clears fruit-anchor, canopy, root, and stability guardrails.",
        ]
    )
    (output_root / "promotion_decision.md").write_text(decision_md, encoding="utf-8")

    plot_spec_path = _resolve_config_path(
        gate_cfg.get("promotion_overlay_spec", "configs/plotkit/tomics/knu_yield_fit_overlay.yaml"),
        repo_root=repo_root,
        config_path=config_path,
    )
    _render_promotion_overlay(
        output_root=output_root,
        scorecard_df=scorecard_df[scorecard_df["candidate_label"].isin(promotion_candidates)],
        holdout_results=holdout_results,
        spec_path=plot_spec_path,
    )
    return {
        "output_root": str(output_root),
        "recommendation": recommendation,
        "incumbent": incumbent,
    }


__all__ = ["run_promotion_gate"]
