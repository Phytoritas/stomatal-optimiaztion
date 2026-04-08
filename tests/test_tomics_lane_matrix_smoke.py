from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pandas as pd
import yaml

from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.datasets.runtime import (
    PreparedDatasetThetaScenario,
    PreparedMeasuredHarvestBundle,
    prepare_measured_harvest_bundle,
)
from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.datasets.registry import (
    load_dataset_registry,
)
from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.harvest_family_eval import (
    HarvestFamilyRunResult,
)
from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.lane_matrix.lane_gate import (
    run_lane_matrix_gate,
)
from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.lane_matrix.matrix_runner import (
    run_lane_matrix,
)

from .tomics_knu_test_helpers import (
    write_minimal_current_base_config,
    write_sampled_knu_forcing,
    write_sampled_knu_yield_fixture,
)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _write_selected_architecture(path: Path, *, architecture_id: str, selected_architecture: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "selected_architecture_id": architecture_id,
                "selected_architecture": selected_architecture,
            },
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )


def _write_selected_harvest_family(repo_root: Path) -> None:
    selected_path = repo_root / "out" / "tomics_knu_harvest_family_factorial" / "selected_harvest_family.json"
    selected_path.parent.mkdir(parents=True, exist_ok=True)
    selected_path.write_text(
        json.dumps(
            {
                "selected_harvest_family_id": "dekoning_fds|vegetative_unit_pruning|dekoning_fds",
                "selected_fruit_harvest_family": "dekoning_fds",
                "selected_leaf_harvest_family": "vegetative_unit_pruning",
                "selected_fdmc_mode": "dekoning_fds",
                "harvest_delay_days": 0.0,
                "harvest_readiness_threshold": 1.0,
                "fruit_params": {"fds_harvest_threshold": 1.0, "fdmc_mode": "dekoning_fds"},
                "leaf_params": {"colour_threshold": 0.9},
                "winner_native_state_fraction": 0.8,
                "winner_proxy_state_fraction": 0.2,
            },
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )


def _write_lane_matrix_fixture_config(
    tmp_path: Path,
    *,
    extra_dataset_items: list[dict[str, object]] | None = None,
) -> tuple[Path, dict[str, object], Path]:
    actual_repo = _repo_root()
    repo_root = tmp_path / "lane-matrix-repo"
    repo_root.mkdir(parents=True, exist_ok=True)
    forcing_path = write_sampled_knu_forcing(tmp_path, sample_every_rows=360, min_days=14)
    yield_path = write_sampled_knu_yield_fixture(tmp_path, min_days=14)
    yield_dates = pd.to_datetime(pd.read_csv(yield_path)["Date"], errors="raise").dt.normalize()
    validation_start = str(yield_dates.min().date())
    validation_end = str(yield_dates.max().date())
    base_config_path = write_minimal_current_base_config(tmp_path, repo_root=actual_repo)
    base_config = yaml.safe_load(base_config_path.read_text(encoding="utf-8"))
    current_row = dict(base_config["stage1"]["candidates"][1])
    promoted_row = {
        **current_row,
        "architecture_id": "constrained_full_plus_feedback__buffer_capacity_g_m2_12p0",
        "partition_policy": "tomics_promoted_research",
        "policy_family": "promoted_selected",
    }
    current_root = repo_root / "out" / "tomics" / "validation" / "knu" / "architecture" / "current-factorial"
    promoted_root = repo_root / "out" / "tomics" / "validation" / "knu" / "architecture" / "promoted-factorial"
    _write_selected_architecture(
        current_root / "selected_architecture.json",
        architecture_id="kuijpers_hybrid_candidate",
        selected_architecture=current_row,
    )
    _write_selected_architecture(
        promoted_root / "selected_architecture.json",
        architecture_id="constrained_full_plus_feedback__buffer_capacity_g_m2_12p0",
        selected_architecture=promoted_row,
    )
    _write_selected_harvest_family(repo_root)
    current_vs_promoted_config_path = tmp_path / "current_vs_promoted.yaml"
    current_vs_promoted_config_path.write_text(
        yaml.safe_dump(
            {
                "current": {"base_config": str(base_config_path)},
                "paths": {
                    "current_output_root": str(current_root),
                    "promoted_output_root": str(promoted_root),
                },
            },
            sort_keys=False,
            allow_unicode=False,
        ),
        encoding="utf-8",
    )
    dataset_items = [
        {
            "dataset_id": "knu_actual",
            "dataset_kind": "knu_measured_harvest",
            "display_name": "KNU actual",
            "forcing_path": str(forcing_path),
            "observed_harvest_path": str(yield_path),
            "validation_start": validation_start,
            "validation_end": validation_end,
            "cultivar": "unknown",
            "greenhouse": "KNU",
            "season": "current_window",
            "basis": {
                "reporting_basis": "floor_area_g_m2",
                "plants_per_m2": 1.836091,
            },
            "observation": {
                "date_column": "Date",
                "measured_cumulative_column": "Measured_Cumulative_Total_Fruit_DW (g/m^2)",
                "estimated_cumulative_column": "Estimated_Cumulative_Total_Fruit_DW (g/m^2)",
                "measured_semantics": "cumulative_harvested_fruit_dry_weight_floor_area",
            },
            "sanitized_fixture": {
                "forcing_fixture_path": str(forcing_path),
                "observed_harvest_fixture_path": str(yield_path),
            },
            "notes": {"dataset_role_hint": "measured_harvest"},
        }
    ]
    if extra_dataset_items:
        dataset_items.extend(extra_dataset_items)
    lane_matrix_config = {
        "paths": {"repo_root": str(repo_root)},
        "validation": {
            "forcing_csv_path": str(forcing_path),
            "yield_xlsx_path": str(yield_path),
            "prepared_output_root": str(repo_root / "out" / "tomics" / "validation" / "knu" / "longrun"),
            "resample_rule": "6h",
            "theta_proxy_mode": "bucket_irrigated",
            "theta_proxy_scenarios": ["moderate"],
            "calibration_end": "2024-08-19",
            "datasets": {
                "default_dataset_ids": ["knu_actual"],
                "items": dataset_items,
            },
            "lane_matrix": {
                "output_root": str(repo_root / "out" / "tomics" / "validation" / "lane-matrix"),
                "theta_proxy_scenario": "moderate",
                "allocation_lane_ids": [
                    "legacy_sink_baseline",
                    "incumbent_current",
                    "research_current",
                    "research_promoted",
                    "raw_reference_thorp",
                ],
                "harvest_profile_ids": ["incumbent_harvest_profile"],
            },
        },
        "reference": {
            "current_vs_promoted_config": str(current_vs_promoted_config_path),
            "current_output_root": str(current_root),
            "promoted_output_root": str(promoted_root),
        },
    }
    config_path = tmp_path / "lane_matrix.yaml"
    config_path.write_text(
        yaml.safe_dump(lane_matrix_config, sort_keys=False, allow_unicode=False),
        encoding="utf-8",
    )
    return config_path, lane_matrix_config, repo_root


def test_lane_matrix_runner_and_gate_smoke_current_knu_mode(tmp_path: Path, monkeypatch) -> None:
    config_path, config, repo_root = _write_lane_matrix_fixture_config(tmp_path)
    yield_path = Path(config["validation"]["yield_xlsx_path"])
    yield_df = pd.read_csv(yield_path).copy()
    yield_df["Date"] = pd.to_datetime(yield_df["Date"], errors="raise").dt.normalize()
    observed_df = pd.DataFrame(
        {
            "date": yield_df["Date"],
            "measured_cumulative_total_fruit_dry_weight_floor_area": yield_df["Measured_Cumulative_Total_Fruit_DW (g/m^2)"],
            "estimated_cumulative_total_fruit_dry_weight_floor_area": yield_df["Estimated_Cumulative_Total_Fruit_DW (g/m^2)"],
        }
    )
    observed_df["measured_daily_increment_floor_area"] = observed_df[
        "measured_cumulative_total_fruit_dry_weight_floor_area"
    ].diff().fillna(observed_df["measured_cumulative_total_fruit_dry_weight_floor_area"])
    def _fake_prepare_measured_harvest_bundle(*args, **kwargs) -> PreparedMeasuredHarvestBundle:
        forcing_path = Path(config["validation"]["forcing_csv_path"])
        scenario = PreparedDatasetThetaScenario(
            scenario_id="moderate",
            minute_df=pd.DataFrame(),
            hourly_df=pd.DataFrame(),
            forcing_csv_path=forcing_path,
            summary={"theta_mean": 0.65},
        )
        return PreparedMeasuredHarvestBundle(
            dataset_id="knu_actual",
            observed_df=observed_df,
            validation_start=pd.Timestamp(observed_df["date"].min()),
            validation_end=pd.Timestamp(observed_df["date"].max()),
            calibration_end=pd.Timestamp(observed_df["date"].iloc[min(5, len(observed_df) - 2)]),
            holdout_start=pd.Timestamp(observed_df["date"].iloc[min(6, len(observed_df) - 1)]),
            prepared_root=repo_root / "out" / "prepared",
            scenarios={"moderate": scenario},
            source_unit_label="g/m^2",
            reporting_basis_in="floor_area_g_m2",
            reporting_basis_canonical="floor_area_g_m2",
            basis_normalization_resolved=True,
            normalization_factor_to_floor_area=1.0,
            manifest_summary={"reporting_basis": "floor_area_g_m2"},
        )

    def _fake_reconstruct_hidden_state(*args, **kwargs):
        return SimpleNamespace(initial_state_overrides={})

    def _fake_run_harvest_family_simulation(*, run_config, observed_df, fruit_harvest_family, **kwargs) -> HarvestFamilyRunResult:
        assert run_config["pipeline"]["model"] == "tomato_legacy"
        partition_policy = str(run_config["pipeline"]["partition_policy"])
        factor = {
            "legacy": 0.98,
            "tomics": 1.00,
            "tomics_alloc_research": 1.02,
            "tomics_promoted_research": 1.01,
            "thorp_fruit_veg": 0.95,
        }[partition_policy]
        validation_df = observed_df.copy()
        validation_df["model_cumulative_harvested_fruit_dry_weight_floor_area"] = (
            validation_df["measured_cumulative_total_fruit_dry_weight_floor_area"] * factor
        )
        validation_df["model_daily_increment_floor_area"] = validation_df[
            "model_cumulative_harvested_fruit_dry_weight_floor_area"
        ].diff().fillna(validation_df["model_cumulative_harvested_fruit_dry_weight_floor_area"])
        run_df = pd.DataFrame(
            {
                "date": validation_df["date"],
                "alloc_frac_fruit": 0.45 if partition_policy == "tomics" else 0.42,
            }
        )
        harvest_mass_balance_df = pd.DataFrame(
            {
                "date": validation_df["date"],
                "harvest_mass_balance_error": 0.0,
                "latent_fruit_residual_end": 0.0,
                "leaf_harvest_mass_balance_error": 0.0,
                "post_writeback_dropped_nonharvested_mass_g_m2": 0.0,
                "offplant_with_positive_mass_flag": False,
            }
        )
        rmse = abs(1.0 - factor)
        metrics = {
            "rmse_cumulative_offset": rmse,
            "rmse_daily_increment": rmse,
            "canopy_collapse_days": 0.0,
            "native_family_state_fraction": 1.0,
            "shared_tdvs_proxy_fraction": 0.0,
            "proxy_family_state_fraction": 0.0 if fruit_harvest_family == "tomsim_truss" else 0.1,
            "post_writeback_dropped_nonharvested_mass_g_m2": 0.0,
            "offplant_with_positive_mass_flag": False,
        }
        return HarvestFamilyRunResult(
            run_df=run_df,
            model_daily_df=validation_df[["date", "model_cumulative_harvested_fruit_dry_weight_floor_area"]].copy(),
            validation_df=validation_df,
            fruit_events_df=pd.DataFrame(),
            leaf_events_df=pd.DataFrame(),
            harvest_mass_balance_df=harvest_mass_balance_df,
            metrics=metrics,
        )

    monkeypatch.setattr(
        "stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.lane_matrix.matrix_runner.prepare_measured_harvest_bundle",
        _fake_prepare_measured_harvest_bundle,
    )
    monkeypatch.setattr(
        "stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.lane_matrix.matrix_runner.reconstruct_hidden_state",
        _fake_reconstruct_hidden_state,
    )
    monkeypatch.setattr(
        "stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.lane_matrix.matrix_runner.run_harvest_family_simulation",
        _fake_run_harvest_family_simulation,
    )

    result = run_lane_matrix(config, repo_root=repo_root, config_path=config_path)
    output_root = Path(result["output_root"])
    assert (output_root / "scenario_index.csv").exists()
    assert (output_root / "lane_scorecard.csv").exists()
    scorecard_df = pd.read_csv(output_root / "lane_scorecard.csv")
    assert {"legacy_sink_baseline", "incumbent_current", "research_current", "research_promoted", "raw_reference_thorp"}.issubset(
        set(scorecard_df["allocation_lane_id"])
    )
    assert scorecard_df.loc[scorecard_df["allocation_lane_id"].eq("legacy_sink_baseline"), "partition_policy"].iloc[0] == "legacy"
    assert scorecard_df.loc[scorecard_df["allocation_lane_id"].eq("incumbent_current"), "partition_policy"].iloc[0] == "tomics"
    assert bool(scorecard_df.loc[scorecard_df["allocation_lane_id"].eq("raw_reference_thorp"), "reference_only"].iloc[0])
    incumbent = scorecard_df.loc[scorecard_df["allocation_lane_id"].eq("incumbent_current")].iloc[0]
    research = scorecard_df.loc[scorecard_df["allocation_lane_id"].eq("research_current")].iloc[0]
    assert incumbent["reporting_basis_canonical"] == "floor_area_g_m2"
    assert research["reporting_basis_canonical"] == "floor_area_g_m2"
    assert incumbent["runtime_complete_semantics"] == research["runtime_complete_semantics"]

    gate_config = {
        "validation": {
            "lane_matrix_gate": {
                "matrix_root": str(output_root),
                "output_root": str(output_root),
                "min_dataset_count": 2,
            }
        }
    }
    gate_result = run_lane_matrix_gate(gate_config, repo_root=repo_root, config_path=config_path)
    assert gate_result["diagnostic_rows"] >= scorecard_df.shape[0]
    assert (output_root / "promotion_surface.csv").exists()
    assert (output_root / "diagnostic_surface.csv").exists()
    assert (output_root / "lane_gate_decision.json").exists()


def test_lane_matrix_keeps_context_only_dataset_diagnostic_only(tmp_path: Path, monkeypatch) -> None:
    config_path, config, repo_root = _write_lane_matrix_fixture_config(tmp_path)
    yield_path = Path(config["validation"]["yield_xlsx_path"])
    yield_df = pd.read_csv(yield_path).copy()
    yield_df["Date"] = pd.to_datetime(yield_df["Date"], errors="raise").dt.normalize()
    validation_start = str(yield_df["Date"].min().date())
    validation_end = str(yield_df["Date"].max().date())
    measured_item = config["validation"]["datasets"]["items"][0]
    config["validation"]["datasets"]["items"].append(
        {
            "dataset_id": "trait_context",
            "dataset_kind": "traitenv_bundle",
            "display_name": "Trait plus env context",
            "forcing_path": str(measured_item["forcing_path"]),
            "observed_harvest_path": str(measured_item["observed_harvest_path"]),
            "validation_start": validation_start,
            "validation_end": validation_end,
            "cultivar": "unknown",
            "greenhouse": "KNU",
            "season": "context_window",
            "basis": {
                "reporting_basis": "floor_area_g_m2",
                "plants_per_m2": 1.836091,
            },
            "observation": {
                "date_column": "Date",
                "measured_cumulative_column": "Measured_Cumulative_Total_Fruit_DW (g/m^2)",
                "estimated_cumulative_column": "Estimated_Cumulative_Total_Fruit_DW (g/m^2)",
                "measured_semantics": "cumulative_harvested_fruit_dry_weight_floor_area",
            },
            "notes": {
                "dataset_role_hint": "trait_plus_env_no_harvest",
            },
        }
    )
    observed_df = pd.DataFrame(
        {
            "date": yield_df["Date"],
            "measured_cumulative_total_fruit_dry_weight_floor_area": yield_df["Measured_Cumulative_Total_Fruit_DW (g/m^2)"],
            "estimated_cumulative_total_fruit_dry_weight_floor_area": yield_df["Estimated_Cumulative_Total_Fruit_DW (g/m^2)"],
        }
    )
    observed_df["measured_daily_increment_floor_area"] = observed_df[
        "measured_cumulative_total_fruit_dry_weight_floor_area"
    ].diff().fillna(observed_df["measured_cumulative_total_fruit_dry_weight_floor_area"])

    def _fake_prepare_measured_harvest_bundle(*args, **kwargs) -> PreparedMeasuredHarvestBundle:
        forcing_path = Path(config["validation"]["forcing_csv_path"])
        scenario = PreparedDatasetThetaScenario(
            scenario_id="moderate",
            minute_df=pd.DataFrame(),
            hourly_df=pd.DataFrame(),
            forcing_csv_path=forcing_path,
            summary={"theta_mean": 0.65},
        )
        return PreparedMeasuredHarvestBundle(
            dataset_id="knu_actual",
            observed_df=observed_df,
            validation_start=pd.Timestamp(observed_df["date"].min()),
            validation_end=pd.Timestamp(observed_df["date"].max()),
            calibration_end=pd.Timestamp(observed_df["date"].iloc[min(5, len(observed_df) - 2)]),
            holdout_start=pd.Timestamp(observed_df["date"].iloc[min(6, len(observed_df) - 1)]),
            prepared_root=repo_root / "out" / "prepared",
            scenarios={"moderate": scenario},
            source_unit_label="g/m^2",
            reporting_basis_in="floor_area_g_m2",
            reporting_basis_canonical="floor_area_g_m2",
            basis_normalization_resolved=True,
            normalization_factor_to_floor_area=1.0,
            manifest_summary={"reporting_basis": "floor_area_g_m2"},
        )

    def _fake_reconstruct_hidden_state(*args, **kwargs):
        return SimpleNamespace(initial_state_overrides={})

    def _fake_run_harvest_family_simulation(*, run_config, observed_df, **kwargs) -> HarvestFamilyRunResult:
        validation_df = observed_df.copy()
        validation_df["model_cumulative_harvested_fruit_dry_weight_floor_area"] = validation_df[
            "measured_cumulative_total_fruit_dry_weight_floor_area"
        ]
        validation_df["model_daily_increment_floor_area"] = validation_df[
            "model_cumulative_harvested_fruit_dry_weight_floor_area"
        ].diff().fillna(validation_df["model_cumulative_harvested_fruit_dry_weight_floor_area"])
        run_df = pd.DataFrame({"date": validation_df["date"], "alloc_frac_fruit": 0.45})
        harvest_mass_balance_df = pd.DataFrame(
            {
                "date": validation_df["date"],
                "post_writeback_dropped_nonharvested_mass_g_m2": 0.0,
                "offplant_with_positive_mass_flag": False,
            }
        )
        return HarvestFamilyRunResult(
            run_df=run_df,
            model_daily_df=validation_df[["date", "model_cumulative_harvested_fruit_dry_weight_floor_area"]].copy(),
            validation_df=validation_df,
            fruit_events_df=pd.DataFrame(),
            leaf_events_df=pd.DataFrame(),
            harvest_mass_balance_df=harvest_mass_balance_df,
            metrics={
                "rmse_cumulative_offset": 0.0,
                "rmse_daily_increment": 0.0,
                "canopy_collapse_days": 0.0,
                "native_family_state_fraction": 1.0,
                "shared_tdvs_proxy_fraction": 0.0,
                "proxy_family_state_fraction": 0.0,
                "post_writeback_dropped_nonharvested_mass_g_m2": 0.0,
                "offplant_with_positive_mass_flag": False,
            },
        )

    monkeypatch.setattr(
        "stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.lane_matrix.matrix_runner.prepare_measured_harvest_bundle",
        _fake_prepare_measured_harvest_bundle,
    )
    monkeypatch.setattr(
        "stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.lane_matrix.matrix_runner.reconstruct_hidden_state",
        _fake_reconstruct_hidden_state,
    )
    monkeypatch.setattr(
        "stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.lane_matrix.matrix_runner.run_harvest_family_simulation",
        _fake_run_harvest_family_simulation,
    )

    output_root = Path(run_lane_matrix(config, repo_root=repo_root, config_path=config_path)["output_root"])
    scorecard_df = pd.read_csv(output_root / "lane_scorecard.csv")
    context_rows = scorecard_df.loc[scorecard_df["dataset_id"].eq("trait_context")].copy()
    assert not context_rows.empty
    assert set(context_rows["dataset_role"]) == {"trait_plus_env_no_harvest"}
    assert set(context_rows["execution_status"]) == {"dataset_role_not_harvest_scoreable"}
    assert not context_rows["execution_status"].eq("scored").any()

    gate_config = {
        "validation": {
            "lane_matrix_gate": {
                "matrix_root": str(output_root),
                "output_root": str(output_root),
                "min_dataset_count": 2,
            }
        }
    }
    run_lane_matrix_gate(gate_config, repo_root=repo_root, config_path=config_path)
    diagnostic_df = pd.read_csv(output_root / "diagnostic_surface.csv")
    decision = json.loads((output_root / "lane_gate_decision.json").read_text(encoding="utf-8"))
    assert "trait_context" in set(diagnostic_df["dataset_id"])
    assert decision["measured_dataset_count"] == 1


def test_lane_matrix_prepared_contract_preserves_observation_metadata(tmp_path: Path) -> None:
    config_path, config, repo_root = _write_lane_matrix_fixture_config(tmp_path)
    prepared_root = tmp_path / "prepared-contract"
    prepared_root.mkdir(parents=True, exist_ok=True)
    dataset_cfg = config["validation"]["datasets"]["items"][0]
    bundle = prepare_measured_harvest_bundle(
        load_dataset_registry(config, repo_root=repo_root, config_path=config_path).require("knu_actual"),
        validation_cfg=config["validation"],
        prepared_root=prepared_root,
    )
    contract_path = prepared_root / "observation_contract_manifest.json"
    contract_payload = json.loads(contract_path.read_text(encoding="utf-8"))

    assert bundle.reporting_basis_in == "floor_area_g_m2"
    assert contract_payload["reporting_basis_in"] == "floor_area_g_m2"
    assert contract_payload["plants_per_m2"] == 1.836091
    assert contract_payload["date_column"] == "Date"
    assert contract_payload["measured_cumulative_column"] == "Measured_Cumulative_Total_Fruit_DW (g/m^2)"
    assert contract_payload["estimated_cumulative_column"] == "Estimated_Cumulative_Total_Fruit_DW (g/m^2)"
    assert contract_payload["validation_start"] == dataset_cfg["validation_start"]
