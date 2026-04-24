from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

import stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.current_vs_promoted as current_vs_promoted

from .tomics_knu_test_helpers import write_minimal_knu_config


def _synthetic_promoted_metrics_row(row: dict[str, object], idx: int) -> dict[str, object]:
    architecture_id = str(row["architecture_id"])
    policy_family = str(row.get("policy_family", ""))
    score = 1.0
    if policy_family == "promoted":
        score = 100.0
    if "constrained_full_plus_feedback" in architecture_id:
        score = 500.0
    if "__fruit_abort_threshold_" in architecture_id:
        score = 700.0

    return {
        **row,
        "score": score,
        "yield_rmse_offset_adjusted": max(0.1, 1000.0 / (score + 1.0)),
        "final_fruit_dry_weight_floor_area": 1000.0 + idx,
        "canopy_collapse_days": 0.0,
        "fruit_anchor_error_vs_legacy": 0.01,
    }


def _synthetic_validation_row(row: dict[str, object], idx: int) -> dict[str, object]:
    model_value = 100.0 + float(idx)
    return {
        "date": pd.Timestamp("2025-01-01"),
        "architecture_id": str(row["architecture_id"]),
        "theta_proxy_scenario": str(row.get("theta_proxy_scenario", "moderate")),
        "fruit_load_regime": str(row.get("fruit_load_regime", "observed_baseline")),
        "candidate_label": "model",
        "measured_cumulative_total_fruit_dry_weight_floor_area": 100.0,
        "measured_offset_adjusted": 0.0,
        "measured_daily_increment_floor_area": 0.0,
        "model_cumulative_total_fruit_dry_weight_floor_area": model_value,
        "model_offset_adjusted": model_value - 100.0,
        "model_daily_increment_floor_area": 0.0,
    }


def test_promoted_factorial_knu_runner_contract_writes_required_outputs(tmp_path: Path, monkeypatch) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    config_path = write_minimal_knu_config(tmp_path, repo_root=repo_root, mode="promoted")
    config = current_vs_promoted.load_config(config_path)
    forcing_path = tmp_path / "forcing.csv"
    forcing_path.write_text("datetime,T_air_C\n2025-01-01 00:00:00,20.0\n", encoding="utf-8")
    prepared_bundle = current_vs_promoted.PreparedKnuBundle(
        data=None,
        data_contract=None,
        observed_df=pd.DataFrame(),
        validation_start=pd.Timestamp("2025-01-01"),
        validation_end=pd.Timestamp("2025-01-01"),
        calibration_end=pd.Timestamp("2025-01-01"),
        holdout_start=pd.Timestamp("2025-01-01"),
        prepared_root=tmp_path / "prepared",
        scenarios={
            "moderate": current_vs_promoted.PreparedThetaScenario(
                scenario_id="moderate",
                minute_df=pd.DataFrame(),
                hourly_df=pd.DataFrame(),
                forcing_csv_path=forcing_path,
                summary={"theta_mean": 0.61},
            )
        },
        workbook_validation_df=pd.DataFrame(),
        workbook_metrics={},
        manifest_summary={},
    )
    current_selected = {
        "architecture_id": "kuijpers_hybrid_candidate",
        "partition_policy": "tomics_alloc_research",
        "policy_family": "current",
        "allocation_scheme": "4pool",
        "wet_root_cap": 0.10,
        "dry_root_cap": 0.18,
        "lai_target_center": 2.75,
        "leaf_fraction_of_shoot_base": 0.72,
        "thorp_root_blend": 1.0,
    }
    execute_stage_sets: list[set[str]] = []
    plot_calls: dict[str, object] = {}
    validation_plot_call: dict[str, object] = {}

    def _fake_execute_rows(
        rows: list[dict[str, object]],
        **_: object,
    ) -> tuple[pd.DataFrame, pd.DataFrame]:
        execute_stage_sets.append({str(row["stage"]) for row in rows})
        metrics = [_synthetic_promoted_metrics_row(row, idx) for idx, row in enumerate(rows)]
        validation = [_synthetic_validation_row(row, idx) for idx, row in enumerate(rows)]
        return pd.DataFrame(metrics), pd.DataFrame(validation)

    def _fake_render_study_plots(
        *,
        output_root: Path,
        metrics_df: pd.DataFrame,
        interaction_df: pd.DataFrame,
        **_: object,
    ) -> dict[str, dict[str, str]]:
        output_root.mkdir(parents=True, exist_ok=True)
        summary_path = output_root / "summary_plot.png"
        main_effects_path = output_root / "main_effects.png"
        summary_path.write_bytes(b"synthetic summary plot")
        main_effects_path.write_bytes(b"synthetic main effects plot")
        plot_calls["architectures"] = set(metrics_df["architecture_id"].astype(str))
        plot_calls["interaction_factors"] = set(interaction_df["factor"].astype(str))
        return {
            "summary": {"out_path": str(summary_path)},
            "main_effects": {"out_path": str(main_effects_path)},
        }

    def _fake_write_study_validation_plots(
        *,
        study_root: Path,
        validation_df: pd.DataFrame,
        selected_architecture_id: str,
        shipped_architecture_id: str,
        **_: object,
    ) -> None:
        validation_plot_call["selected_architecture_id"] = selected_architecture_id
        validation_plot_call["shipped_architecture_id"] = shipped_architecture_id
        validation_plot_call["architectures"] = set(validation_df["architecture_id"].astype(str))
        plot_root = study_root / "validation_plots"
        plot_root.mkdir(parents=True, exist_ok=True)
        (plot_root / "yield_fit_overlay.png").write_bytes(b"synthetic validation plot")

    monkeypatch.setattr(current_vs_promoted, "_execute_rows", _fake_execute_rows)
    monkeypatch.setattr(current_vs_promoted, "_render_study_plots", _fake_render_study_plots)
    monkeypatch.setattr(current_vs_promoted, "_write_study_validation_plots", _fake_write_study_validation_plots)
    monkeypatch.setattr(
        current_vs_promoted,
        "run_tomato_legacy_pipeline",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("synthetic test must not run TOMICS")),
    )

    result = current_vs_promoted.run_promoted_factorial_knu(
        config,
        repo_root=repo_root,
        config_path=config_path,
        prepared_bundle=prepared_bundle,
        current_selected=current_selected,
    )
    output_root = Path(result["output_root"])

    required = {
        "design_table.csv",
        "run_metrics.csv",
        "interaction_summary.csv",
        "candidate_ranking.csv",
        "selected_architecture.json",
        "decision_bundle.md",
        "validation_vs_measured.csv",
        "summary_plot.png",
        "main_effects.png",
    }
    assert all((output_root / name).exists() for name in required)
    assert (output_root / "validation_plots" / "yield_fit_overlay.png").exists()
    assert execute_stage_sets == [{"p0"}, {"p1"}, {"p2"}, {"p3"}]

    design_df = pd.read_csv(output_root / "design_table.csv")
    assert design_df["stage"].value_counts().to_dict()["p0"] == 5
    assert design_df["stage"].value_counts().to_dict()["p2"] == 13

    metrics_df = pd.read_csv(output_root / "run_metrics.csv")
    promoted_rows = metrics_df[metrics_df["policy_family"].eq("promoted")]
    assert {
        "optimizer_mode",
        "vegetative_prior_mode",
        "leaf_marginal_mode",
        "stem_marginal_mode",
        "root_marginal_mode",
    }.issubset(promoted_rows.columns)
    assert "constrained_full_plus_feedback" in {
        str(value).split("__", maxsplit=1)[0] for value in plot_calls["architectures"]
    }
    assert "fruit_feedback_mode" in plot_calls["interaction_factors"]

    selected_payload = json.loads((output_root / "selected_architecture.json").read_text(encoding="utf-8"))
    selected_id = selected_payload["selected_architecture_id"]
    assert selected_id.startswith("constrained_full_plus_feedback")
    assert validation_plot_call["selected_architecture_id"] == selected_id
    assert validation_plot_call["shipped_architecture_id"] == "shipped_tomics_control"
    assert selected_id in validation_plot_call["architectures"]
