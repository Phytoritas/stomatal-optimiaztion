from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pandas as pd

from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.observation_eval import (
    run_knu_observation_eval,
)
from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.parameter_budget import (
    CalibrationCandidate,
)

from .tomics_knu_test_helpers import write_minimal_fairness_config


def _observed_fixture_frame() -> pd.DataFrame:
    dates = pd.date_range("2024-08-20", periods=3, freq="D")
    measured = [10.0, 20.0, 30.0]
    estimated = [11.0, 19.0, 29.0]
    return pd.DataFrame(
        {
            "date": dates,
            "measured_cumulative_total_fruit_dry_weight_floor_area": measured,
            "measured_offset_adjusted": [value - measured[0] for value in measured],
            "measured_daily_increment_floor_area": [0.0, 10.0, 10.0],
            "estimated_cumulative_total_fruit_dry_weight_floor_area": estimated,
            "estimated_offset_adjusted": [value - estimated[0] for value in estimated],
            "estimated_daily_increment_floor_area": [0.0, 8.0, 10.0],
        }
    )


def test_observation_eval_runner_contract_writes_summary_manifest_and_overlays(
    tmp_path: Path,
    monkeypatch,
) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    config_path = write_minimal_fairness_config(
        tmp_path,
        repo_root=repo_root,
        filename="knu_observation_eval.yaml",
        section_name="observation_eval",
        section_payload={
            "cumulative_overlay_spec": "configs/plotkit/tomics/knu_cumulative_overlay.yaml",
            "daily_overlay_spec": "configs/plotkit/tomics/knu_daily_increment_overlay.yaml",
        },
    )

    observed_df = _observed_fixture_frame()
    forcing_path = tmp_path / "forcing.csv"
    forcing_path.write_text("datetime,T_air_C\n2024-08-20 00:00:00,25.0\n", encoding="utf-8")
    prepared_bundle = SimpleNamespace(
        observed_df=observed_df,
        workbook_validation_df=observed_df,
        workbook_metrics={
            "reporting_basis": "floor_area_g_m2",
            "yield_rmse_raw": 0.0,
            "yield_rmse_offset_adjusted": 0.0,
        },
        data=SimpleNamespace(observation_unit_label="g/m^2"),
        data_contract=SimpleNamespace(plants_per_m2=1.836091),
        scenarios={
            "moderate": SimpleNamespace(
                forcing_csv_path=forcing_path,
                summary={"theta_mean": 0.65},
            )
        },
    )
    candidates = [
        CalibrationCandidate(
            candidate_label="workbook_estimated",
            architecture_id="workbook_estimated_baseline",
            candidate_role="comparator",
            calibratable=False,
            row={"architecture_id": "workbook_estimated_baseline"},
        ),
        CalibrationCandidate(
            candidate_label="shipped_tomics",
            architecture_id="shipped_tomics_control",
            candidate_role="incumbent",
            calibratable=True,
            row={"architecture_id": "shipped_tomics_control", "partition_policy": "tomics"},
        ),
        CalibrationCandidate(
            candidate_label="current_selected",
            architecture_id="kuijpers_hybrid_candidate",
            candidate_role="research_current",
            calibratable=True,
            row={"architecture_id": "kuijpers_hybrid_candidate", "partition_policy": "tomics_alloc_research"},
        ),
        CalibrationCandidate(
            candidate_label="promoted_selected",
            architecture_id="constrained_full_plus_feedback__buffer_capacity_g_m2_12p0",
            candidate_role="research_promoted",
            calibratable=True,
            row={
                "architecture_id": "constrained_full_plus_feedback__buffer_capacity_g_m2_12p0",
                "partition_policy": "tomics_promoted_research",
            },
        ),
    ]

    monkeypatch.setattr(
        "stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.observation_eval.prepare_knu_bundle",
        lambda config, repo_root, config_path: prepared_bundle,
    )
    monkeypatch.setattr(
        "stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.observation_eval.load_fairness_candidates",
        lambda fairness_config, repo_root, config_path: (
            SimpleNamespace(),
            candidates,
            {"base_config": {"pipeline": {"model": "tomato_legacy"}}},
        ),
    )
    monkeypatch.setattr(
        "stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.observation_eval.configure_candidate_run",
        lambda **kwargs: {"pipeline": "stub"},
    )
    monkeypatch.setattr(
        "stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.observation_eval.run_tomato_legacy_pipeline",
        lambda run_cfg, repo_root: pd.DataFrame({"datetime": observed_df["date"]}),
    )
    monkeypatch.setattr(
        "stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.observation_eval.model_floor_area_cumulative_total_fruit",
        lambda run_df: pd.DataFrame(
            {
                "date": observed_df["date"],
                "model_cumulative_total_fruit_dry_weight_floor_area": [9.0, 21.0, 31.0],
            }
        ),
    )
    monkeypatch.setattr(
        "stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.observation_eval.render_partition_compare_bundle",
        lambda runs, out_path, spec_path: out_path.write_bytes(b"png"),
    )

    result = run_knu_observation_eval(config_path=config_path)
    output_root = Path(result["output_root"])

    assert (output_root / "observation_fit_summary.csv").exists()
    assert (output_root / "cumulative_overlay.png").exists()
    assert (output_root / "daily_increment_overlay.png").exists()
    manifest = json.loads((output_root / "observation_operator_manifest.json").read_text(encoding="utf-8"))
    assert manifest["observation_operator"]["measured_target"] == "cumulative_harvested_fruit_dry_weight_floor_area"
    assert manifest["reporting_basis"] == "floor_area_g_m2"
    assert manifest["plants_per_m2"] == 1.836091

    summary_df = pd.read_csv(output_root / "observation_fit_summary.csv")
    assert {"workbook_estimated", "shipped_tomics", "current_selected", "promoted_selected"}.issubset(
        set(summary_df["candidate_label"])
    )
