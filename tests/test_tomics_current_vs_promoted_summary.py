from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

import stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.current_vs_promoted as current_vs_promoted


class _SyntheticPlotArtifacts:
    def __init__(self, out_path: Path) -> None:
        self.out_path = out_path

    def to_summary(self) -> dict[str, str]:
        return {"out_path": str(self.out_path)}


def _fake_plot_bundle(*, out_path: Path, **kwargs: object) -> _SyntheticPlotArtifacts:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(b"synthetic plot")
    return _SyntheticPlotArtifacts(out_path)


def _metric_row(
    *,
    stage: str,
    architecture_id: str,
    partition_policy: str,
    rmse: float,
) -> dict[str, object]:
    return {
        "stage": stage,
        "architecture_id": architecture_id,
        "partition_policy": partition_policy,
        "theta_proxy_scenario": "moderate",
        "fruit_load_regime": "observed_baseline",
        "yield_rmse_offset_adjusted": rmse,
        "yield_r2_offset_adjusted": 0.9,
        "canopy_collapse_days": 0.0,
        "wet_condition_root_excess_penalty": 0.0,
        "fruit_anchor_error_vs_legacy": 0.01,
        "final_window_error": 0.02,
    }


def _validation_frame(architecture_ids: dict[str, float]) -> pd.DataFrame:
    dates = pd.date_range("2025-01-01", periods=3, freq="D")
    rows: list[dict[str, object]] = []
    measured = [0.0, 10.0, 20.0]
    for architecture_id, scale in architecture_ids.items():
        model = [value * scale for value in measured]
        rows.extend(
            {
                "date": date,
                "architecture_id": architecture_id,
                "theta_proxy_scenario": "moderate",
                "fruit_load_regime": "observed_baseline",
                "measured_cumulative_total_fruit_dry_weight_floor_area": measured[idx],
                "measured_offset_adjusted": measured[idx],
                "measured_daily_increment_floor_area": measured[idx] - measured[idx - 1] if idx else measured[idx],
                "model_cumulative_total_fruit_dry_weight_floor_area": model[idx],
                "model_offset_adjusted": model[idx],
                "model_daily_increment_floor_area": model[idx] - model[idx - 1] if idx else model[idx],
            }
            for idx, date in enumerate(dates)
        )
    return pd.DataFrame(rows)


def _workbook_validation_frame() -> pd.DataFrame:
    dates = pd.date_range("2025-01-01", periods=3, freq="D")
    estimated = [0.0, 9.0, 18.0]
    return pd.DataFrame(
        {
            "date": dates,
            "estimated_cumulative_total_fruit_dry_weight_floor_area": estimated,
            "estimated_offset_adjusted": estimated,
            "estimated_daily_increment_floor_area": [0.0, 9.0, 9.0],
        }
    )


def test_current_vs_promoted_summary_bundle_writer_contract(tmp_path: Path, monkeypatch) -> None:
    plot_calls: dict[str, dict[str, object]] = {}
    configured_policies: list[str] = []
    executed_policies: list[str] = []

    def _recording_plot_bundle(*, out_path: Path, **kwargs: object) -> _SyntheticPlotArtifacts:
        plot_calls[out_path.name] = dict(kwargs)
        return _fake_plot_bundle(out_path=out_path, **kwargs)

    def _fake_candidate_run(base_config: dict[str, object], *, forcing_csv_path: Path, theta_center: float, row: dict[str, object]) -> dict[str, object]:
        policy = str(row["partition_policy"])
        configured_policies.append(policy)
        return {"pipeline": {"partition_policy": policy}}

    def _fake_tomato_pipeline(run_config: dict[str, object]) -> pd.DataFrame:
        pipeline = run_config["pipeline"]
        assert isinstance(pipeline, dict)
        executed_policies.append(str(pipeline["partition_policy"]))
        return pd.DataFrame({"date": pd.date_range("2025-01-01", periods=3, freq="D")})

    monkeypatch.setattr(current_vs_promoted, "render_architecture_summary_bundle", _recording_plot_bundle)
    monkeypatch.setattr(current_vs_promoted, "render_partition_compare_bundle", _recording_plot_bundle)
    monkeypatch.setattr(
        current_vs_promoted,
        "configure_candidate_run",
        _fake_candidate_run,
    )
    monkeypatch.setattr(
        current_vs_promoted,
        "run_tomato_legacy_pipeline",
        _fake_tomato_pipeline,
    )

    forcing_path = tmp_path / "forcing.csv"
    forcing_path.write_text("datetime,T_air_C\n2025-01-01 00:00:00,20.0\n", encoding="utf-8")
    prepared_bundle = current_vs_promoted.PreparedKnuBundle(
        data=None,
        data_contract=None,
        observed_df=pd.DataFrame(),
        validation_start=pd.Timestamp("2025-01-01"),
        validation_end=pd.Timestamp("2025-01-03"),
        calibration_end=pd.Timestamp("2025-01-02"),
        holdout_start=pd.Timestamp("2025-01-03"),
        prepared_root=tmp_path / "prepared",
        scenarios={
            "moderate": current_vs_promoted.PreparedThetaScenario(
                scenario_id="moderate",
                minute_df=pd.DataFrame(),
                hourly_df=pd.DataFrame(
                    {
                        "datetime": pd.date_range("2025-01-01", periods=3, freq="h"),
                        "theta_substrate": [0.60, 0.61, 0.62],
                    }
                ),
                forcing_csv_path=forcing_path,
                summary={"theta_mean": 0.61},
            )
        },
        workbook_validation_df=_workbook_validation_frame(),
        workbook_metrics={},
        manifest_summary={},
    )
    current_result = {
        "selected_payload": {"selected_architecture_id": "current_selected_id"},
        "metrics_df": pd.DataFrame(
            [
                _metric_row(
                    stage="stage3",
                    architecture_id="shipped_tomics_control",
                    partition_policy="tomics",
                    rmse=0.50,
                ),
                _metric_row(
                    stage="stage3",
                    architecture_id="current_selected_id",
                    partition_policy="tomics_alloc_research",
                    rmse=0.30,
                ),
            ]
        ),
        "validation_df": _validation_frame({"current_selected_id": 1.02}),
    }
    promoted_result = {
        "selected_payload": {"selected_architecture_id": "promoted_selected_id"},
        "metrics_df": pd.DataFrame(
            [
                _metric_row(
                    stage="p3",
                    architecture_id="shipped_tomics_control",
                    partition_policy="tomics",
                    rmse=0.50,
                ),
                _metric_row(
                    stage="p3",
                    architecture_id="promoted_selected_id",
                    partition_policy="tomics_promoted_research",
                    rmse=0.20,
                ),
            ]
        ),
        "validation_df": _validation_frame(
            {
                "shipped_tomics_control": 1.00,
                "promoted_selected_id": 0.99,
            }
        ),
    }

    config_path = tmp_path / "current_vs_promoted.yaml"
    config_path.write_text("paths: {}\n", encoding="utf-8")
    result = current_vs_promoted.write_side_by_side_bundle(
        {"paths": {"comparison_output_root": str(tmp_path / "comparison")}},
        repo_root=Path(__file__).resolve().parents[1],
        config_path=config_path,
        prepared_bundle=prepared_bundle,
        current_result=current_result,
        promoted_result=promoted_result,
    )
    output_root = Path(result["output_root"])

    required = {
        "comparison_summary.csv",
        "architecture_promotion_scorecard.csv",
        "current_vs_promoted_plot.png",
        "yield_fit_overlay.png",
        "allocation_behavior_overlay.png",
        "theta_proxy_diagnostics.png",
        "canonical_winners.json",
        "promotion_recommendation.md",
    }
    assert all((output_root / name).exists() for name in required)

    scorecard = pd.read_csv(output_root / "architecture_promotion_scorecard.csv")
    assert {"candidate_label", "mean_yield_rmse_offset_adjusted"}.issubset(scorecard.columns)
    assert {"shipped_tomics", "current_selected", "promoted_selected"}.issubset(
        set(scorecard["candidate_label"])
    )
    winners = json.loads((output_root / "canonical_winners.json").read_text(encoding="utf-8"))
    assert winners["current_selected_architecture_id"] == "current_selected_id"
    assert winners["promoted_selected_architecture_id"] == "promoted_selected_id"
    assert result["recommendation"] == "next shipped-default candidate"
    assert set(plot_calls) == {
        "current_vs_promoted_plot.png",
        "yield_fit_overlay.png",
        "allocation_behavior_overlay.png",
        "theta_proxy_diagnostics.png",
    }
    assert {
        "shipped_tomics",
        "current_selected",
        "promoted_selected",
    }.issubset(set(plot_calls["current_vs_promoted_plot.png"]["metrics_df"]["candidate_label"]))
    assert set(plot_calls["yield_fit_overlay.png"]["runs"]) == {
        "measured",
        "workbook_estimated",
        "shipped_tomics",
        "current_selected",
        "promoted_selected",
    }
    assert set(plot_calls["allocation_behavior_overlay.png"]["runs"]) == {
        "shipped_tomics",
        "current_selected",
        "promoted_selected",
    }
    assert set(plot_calls["theta_proxy_diagnostics.png"]["runs"]) == {"moderate"}
    assert configured_policies == ["tomics", "tomics_alloc_research", "tomics_promoted_research"]
    assert executed_policies == configured_policies
