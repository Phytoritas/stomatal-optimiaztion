from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.promotion_gate import (
    run_promotion_gate,
)


def _write_validation_series(
    tmp_path: Path,
    *,
    source_label: str,
    cumulative_values: list[float],
) -> Path:
    measured_values = [10.0, 20.0, 30.0]
    frame = pd.DataFrame(
        {
            "date": pd.date_range("2024-08-20", periods=3, freq="D"),
            "measured_cumulative_total_fruit_dry_weight_floor_area": measured_values,
            "measured_offset_adjusted": [value - measured_values[0] for value in measured_values],
            "measured_daily_increment_floor_area": [0.0, 10.0, 10.0],
            f"{source_label}_cumulative_total_fruit_dry_weight_floor_area": cumulative_values,
            f"{source_label}_offset_adjusted": [value - cumulative_values[0] for value in cumulative_values],
            f"{source_label}_daily_increment_floor_area": [
                0.0,
                cumulative_values[1] - cumulative_values[0],
                cumulative_values[2] - cumulative_values[1],
            ],
        }
    )
    out_path = tmp_path / f"{source_label}_validation_series.csv"
    frame.to_csv(out_path, index=False)
    return out_path


def test_promotion_gate_contract_promotes_best_guardrail_passing_candidate(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    calibration_root = tmp_path / "out" / "tomics" / "validation" / "knu" / "fairness" / "calibration"
    calibration_root.mkdir(parents=True, exist_ok=True)

    shipped_series = _write_validation_series(
        tmp_path,
        source_label="shipped_tomics",
        cumulative_values=[10.0, 19.0, 28.0],
    )
    current_series = _write_validation_series(
        tmp_path,
        source_label="current_selected",
        cumulative_values=[10.0, 21.0, 31.0],
    )
    promoted_series = _write_validation_series(
        tmp_path,
        source_label="promoted_selected",
        cumulative_values=[10.0, 22.0, 32.0],
    )
    workbook_series = _write_validation_series(
        tmp_path,
        source_label="workbook_estimated",
        cumulative_values=[10.0, 18.0, 27.0],
    )

    holdout_results = pd.DataFrame(
        [
            {
                "candidate_label": "workbook_estimated",
                "architecture_id": "workbook_estimated_baseline",
                "split_label": "blocked_holdout",
                "holdout_rmse_cumulative_offset": 1.80,
                "holdout_mae_cumulative_offset": 1.50,
                "holdout_r2_cumulative_offset": 0.50,
                "holdout_rmse_daily_increment": 0.70,
                "holdout_mae_daily_increment": 0.60,
                "holdout_final_bias": -3.00,
                "fruit_anchor_error_vs_legacy": 0.00,
                "canopy_collapse_days": 0.0,
                "wet_condition_root_excess_penalty": 0.0,
                "parameter_instability_score": 0.0,
                "validation_series_csv": str(workbook_series),
            },
            {
                "candidate_label": "shipped_tomics",
                "architecture_id": "shipped_tomics_control",
                "split_label": "blocked_holdout",
                "holdout_rmse_cumulative_offset": 1.00,
                "holdout_mae_cumulative_offset": 0.80,
                "holdout_r2_cumulative_offset": 0.80,
                "holdout_rmse_daily_increment": 0.40,
                "holdout_mae_daily_increment": 0.35,
                "holdout_final_bias": -2.00,
                "fruit_anchor_error_vs_legacy": 0.00,
                "canopy_collapse_days": 0.0,
                "wet_condition_root_excess_penalty": 0.01,
                "parameter_instability_score": 0.05,
                "validation_series_csv": str(shipped_series),
            },
            {
                "candidate_label": "current_selected",
                "architecture_id": "kuijpers_hybrid_candidate",
                "split_label": "blocked_holdout",
                "holdout_rmse_cumulative_offset": 0.35,
                "holdout_mae_cumulative_offset": 0.28,
                "holdout_r2_cumulative_offset": 0.95,
                "holdout_rmse_daily_increment": 0.20,
                "holdout_mae_daily_increment": 0.16,
                "holdout_final_bias": 1.00,
                "fruit_anchor_error_vs_legacy": 0.01,
                "canopy_collapse_days": 0.0,
                "wet_condition_root_excess_penalty": 0.01,
                "parameter_instability_score": 0.10,
                "validation_series_csv": str(current_series),
            },
            {
                "candidate_label": "promoted_selected",
                "architecture_id": "constrained_full_plus_feedback__buffer_capacity_g_m2_12p0",
                "split_label": "blocked_holdout",
                "holdout_rmse_cumulative_offset": 0.25,
                "holdout_mae_cumulative_offset": 0.20,
                "holdout_r2_cumulative_offset": 0.97,
                "holdout_rmse_daily_increment": 0.15,
                "holdout_mae_daily_increment": 0.12,
                "holdout_final_bias": 2.00,
                "fruit_anchor_error_vs_legacy": 0.01,
                "canopy_collapse_days": 0.0,
                "wet_condition_root_excess_penalty": 0.01,
                "parameter_instability_score": 0.10,
                "validation_series_csv": str(promoted_series),
            },
        ]
    )
    holdout_results.to_csv(calibration_root / "holdout_results.csv", index=False)

    winner_stability = pd.DataFrame(
        [
            {"candidate_label": "workbook_estimated", "win_fraction": 0.0},
            {"candidate_label": "shipped_tomics", "win_fraction": 0.20},
            {"candidate_label": "current_selected", "win_fraction": 0.60},
            {"candidate_label": "promoted_selected", "win_fraction": 0.70},
        ]
    )
    winner_stability.to_csv(calibration_root / "winner_stability.csv", index=False)
    pd.DataFrame([{"parameter_name": "fruit_load_multiplier", "stability_score": 0.10}]).to_csv(
        calibration_root / "parameter_stability.csv",
        index=False,
    )

    config = {
        "calibration": {
            "output_root": str(calibration_root),
        },
        "promotion_gate": {
            "output_root": str(tmp_path / "out" / "tomics" / "validation" / "knu" / "fairness" / "promotion-gate"),
            "material_rmse_margin": 0.5,
            "material_rmse_fraction": 0.02,
            "wet_root_penalty_max": 0.05,
            "parameter_instability_score_max": 0.50,
            "promotion_overlay_spec": "configs/plotkit/tomics/knu_yield_fit_overlay.yaml",
        },
    }

    decision = run_promotion_gate(
        config,
        repo_root=repo_root,
        config_path=tmp_path / "promotion_gate_contract.yaml",
    )
    promotion_root = Path(decision["output_root"])

    assert decision["incumbent"] == "promoted_selected"
    assert (promotion_root / "promotion_scorecard.csv").exists()
    assert (promotion_root / "promotion_decision.md").exists()
    assert (promotion_root / "promotion_guardrails.json").exists()
    assert (promotion_root / "promotion_holdout_overlay.png").exists()
    assert (promotion_root / "winner_stability.csv").exists()

    scorecard_df = pd.read_csv(promotion_root / "promotion_scorecard.csv")
    assert {
        "workbook_estimated",
        "shipped_tomics",
        "current_selected",
        "promoted_selected",
    }.issubset(set(scorecard_df["candidate_label"]))

    guardrails = json.loads((promotion_root / "promotion_guardrails.json").read_text(encoding="utf-8"))
    assert guardrails["promotion_allowed"] is True
    assert guardrails["incumbent"] == "promoted_selected"
    assert guardrails["current_selected"]["passes"] is True
    assert guardrails["promoted_selected"]["passes"] is True
    assert guardrails["parameter_stability_rows"] == 1

    decision_md = (promotion_root / "promotion_decision.md").read_text(encoding="utf-8")
    assert "promote promoted research allocator as next shipped-default candidate" in decision_md
    assert "Incumbent after fair validation: `promoted_selected`" in decision_md
