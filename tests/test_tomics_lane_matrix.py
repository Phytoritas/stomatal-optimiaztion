from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest
import yaml

from stomatal_optimiaztion.domains.tomato.tomics.alloc.core import load_config
from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.current_vs_promoted import (
    run_current_vs_promoted_factorial,
)
from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.datasets.contracts import (
    DatasetBasisContract,
    DatasetManagementMetadata,
    DatasetMetadataContract,
    DatasetObservationContract,
    DatasetSanitizedFixtureContract,
)
from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.datasets.registry import (
    DatasetRegistry,
)
from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.harvest_calibration_bridge import (
    load_harvest_base_config,
    load_harvest_candidates,
)
from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.harvest_factorial import (
    run_harvest_family_factorial,
)
from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.lane_matrix import (
    resolve_dataset_roles,
    run_lane_matrix,
    run_lane_matrix_gate,
)
from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.lane_matrix.dataset_role_registry import (
    infer_dataset_role,
)
from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.lane_matrix.lane_scorecard import (
    RUNTIME_COMPLETE_SEMANTICS,
    promotion_audit_passes,
)

from .tomics_knu_test_helpers import (
    write_minimal_knu_config,
    write_minimal_knu_harvest_factorial_config,
    write_sampled_knu_forcing,
    write_sampled_knu_yield_fixture,
)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _fixture_dataset(
    *,
    tmp_path: Path,
    dataset_id: str,
    dataset_kind: str,
    notes: dict[str, object] | None = None,
    reporting_basis: str = "floor_area_g_m2",
) -> DatasetMetadataContract:
    forcing_path = tmp_path / f"{dataset_id}_forcing.csv"
    forcing_path.write_text("datetime,T_air_C,PAR_umol,CO2_ppm,RH_percent,wind_speed_ms\n", encoding="utf-8")
    observed_path = tmp_path / f"{dataset_id}_harvest.csv"
    observed_path.write_text("date,measured,estimated\n2025-01-01,0,0\n", encoding="utf-8")
    return DatasetMetadataContract(
        dataset_id=dataset_id,
        dataset_kind=dataset_kind,
        display_name=dataset_id,
        forcing_path=forcing_path,
        observed_harvest_path=observed_path,
        validation_start="2025-01-01",
        validation_end="2025-01-31",
        cultivar="cv",
        greenhouse="gh",
        season="winter",
        basis=DatasetBasisContract(reporting_basis=reporting_basis, plants_per_m2=1.7),
        observation=DatasetObservationContract(
            date_column="date",
            measured_cumulative_column="measured",
            estimated_cumulative_column="estimated",
            measured_semantics="cumulative_harvested_fruit_dry_weight_floor_area",
        ),
        management=DatasetManagementMetadata(),
        sanitized_fixture=DatasetSanitizedFixtureContract(
            forcing_fixture_path=forcing_path,
            observed_harvest_fixture_path=observed_path,
        ),
        notes=notes or {},
    )


def _write_lane_matrix_config(
    tmp_path: Path,
    *,
    repo_root: Path,
    current_vs_promoted_config: Path,
    current_output_root: Path,
    promoted_output_root: Path,
    selected_harvest_family_path: Path,
    forcing_path: Path,
    yield_path: Path,
    dataset_items: list[dict[str, object]] | None = None,
) -> Path:
    yield_frame = pd.read_csv(yield_path)
    yield_dates = pd.to_datetime(yield_frame["Date"], errors="raise").dt.normalize()
    validation_start = str(yield_dates.min().date())
    validation_end = str(yield_dates.max().date())
    items = dataset_items or [
        {
            "dataset_id": "knu_actual",
            "dataset_kind": "knu_measured_harvest",
            "display_name": "KNU measured harvest longrun",
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
            "notes": {
                "dataset_role_hint": "measured_harvest",
            },
        }
    ]
    config = {
        "exp": {"name": "tomics_lane_matrix_test"},
        "paths": {"repo_root": str(repo_root)},
        "validation": {
            "forcing_csv_path": str(forcing_path),
            "yield_xlsx_path": str(yield_path),
            "prepared_output_root": str(tmp_path / "out" / "tomics" / "validation" / "knu" / "longrun"),
            "resample_rule": "6h",
            "theta_proxy_mode": "bucket_irrigated",
            "theta_proxy_scenarios": ["moderate"],
            "calibration_end": "2024-08-19",
            "datasets": {
                "default_dataset_ids": [str(items[0]["dataset_id"])],
                "items": items,
            },
            "lane_matrix": {
                "output_root": str(tmp_path / "out" / "tomics" / "validation" / "lane-matrix"),
                "theta_proxy_scenario": "moderate",
                "selected_harvest_family_path": str(selected_harvest_family_path),
                "allocation_lane_ids": [
                    "legacy_sink_baseline",
                    "incumbent_current",
                    "research_current",
                ],
                "harvest_profile_ids": [
                    "incumbent_harvest_profile",
                    "locked_research_selected_harvest_profile",
                ],
            },
        },
        "reference": {
            "current_vs_promoted_config": str(current_vs_promoted_config),
            "current_output_root": str(current_output_root),
            "promoted_output_root": str(promoted_output_root),
        },
    }
    out_path = tmp_path / "tomics_lane_matrix_test.yaml"
    out_path.write_text(yaml.safe_dump(config, sort_keys=False, allow_unicode=False), encoding="utf-8")
    return out_path


def _write_lane_matrix_gate_config(tmp_path: Path, *, repo_root: Path, matrix_root: Path) -> Path:
    config = {
        "exp": {"name": "tomics_lane_matrix_gate_test"},
        "paths": {"repo_root": str(repo_root)},
        "validation": {
            "lane_matrix_gate": {
                "matrix_root": str(matrix_root),
                "output_root": str(matrix_root),
                "native_state_coverage_min": 0.5,
                "shared_tdvs_proxy_fraction_max": 0.5,
                "cross_dataset_stability_score_min": 0.5,
                "min_dataset_count": 2,
            }
        },
    }
    out_path = tmp_path / "tomics_lane_matrix_gate_test.yaml"
    out_path.write_text(yaml.safe_dump(config, sort_keys=False, allow_unicode=False), encoding="utf-8")
    return out_path


def test_dataset_roles_separate_measured_context_and_yield_environment(tmp_path: Path) -> None:
    measured = _fixture_dataset(
        tmp_path=tmp_path,
        dataset_id="measured",
        dataset_kind="knu_measured_harvest",
        notes={"dataset_role_hint": "measured_harvest", "observation_family": "measured_harvest"},
    )
    trait_env = _fixture_dataset(
        tmp_path=tmp_path,
        dataset_id="trait_env",
        dataset_kind="traitenv_bundle",
        notes={"source_family": "school_trait_bundle", "observation_family": "traitenv"},
    )
    yield_environment = _fixture_dataset(
        tmp_path=tmp_path,
        dataset_id="yield_environment",
        dataset_kind="yield_environment_fixture",
        notes={"dataset_family": "yield_environment", "observation_family": "yield_environment"},
    )
    registry = DatasetRegistry(
        datasets=(measured, trait_env, yield_environment),
        default_dataset_ids=("measured",),
    )
    roles = {row.dataset_id: row for row in resolve_dataset_roles(registry)}

    assert roles["measured"].dataset_role == "measured_harvest"
    assert roles["trait_env"].dataset_role == "trait_plus_env_no_harvest"
    assert roles["yield_environment"].dataset_role == "yield_environment_only"
    assert infer_dataset_role(yield_environment) != "measured_harvest"


def test_promotion_audit_exclusions_cover_basis_and_writeback_flags() -> None:
    clean_payload = {
        "any_all_zero_harvest_series": False,
        "dropped_nonharvested_mass_g_m2": 0.0,
        "offplant_with_positive_mass_flag": False,
        "runtime_complete_semantics": RUNTIME_COMPLETE_SEMANTICS,
        "basis_normalization_resolved": True,
    }
    clean = pd.Series(clean_payload)
    assert promotion_audit_passes(clean)

    assert not promotion_audit_passes(pd.Series({**clean_payload, "any_all_zero_harvest_series": True}))
    assert not promotion_audit_passes(pd.Series({**clean_payload, "dropped_nonharvested_mass_g_m2": 0.1}))
    assert not promotion_audit_passes(pd.Series({**clean_payload, "offplant_with_positive_mass_flag": True}))
    assert not promotion_audit_passes(pd.Series({**clean_payload, "basis_normalization_resolved": False}))


def test_lane_gate_keeps_raw_reference_only_in_diagnostics(tmp_path: Path) -> None:
    matrix_root = tmp_path / "lane_matrix"
    matrix_root.mkdir(parents=True, exist_ok=True)
    scorecard = pd.DataFrame(
        [
            {
                "scenario_id": "research_current__profile__dataset_a",
                "allocation_lane_id": "research_current",
                "harvest_profile_id": "locked_research_selected_harvest_profile",
                "dataset_id": "dataset_a",
                "dataset_role": "measured_harvest",
                "promotion_eligible": True,
                "reference_only": False,
                "reporting_basis_in": "floor_area_g_m2",
                "reporting_basis_canonical": "floor_area_g_m2",
                "basis_normalization_resolved": True,
                "rmse_cumulative_offset": 1.0,
                "rmse_daily_increment": 0.4,
                "fruit_anchor_error": 0.05,
                "canopy_collapse_days": 0.0,
                "winner_stability_score": 1.0,
                "native_state_coverage": 0.9,
                "shared_tdvs_proxy_fraction": 0.1,
                "family_separability_score": 0.8,
                "any_all_zero_harvest_series": False,
                "dropped_nonharvested_mass_g_m2": 0.0,
                "offplant_with_positive_mass_flag": False,
                "runtime_complete_semantics": RUNTIME_COMPLETE_SEMANTICS,
                "selected_family_label": "locked",
                "selected_family_is_native": True,
                "selected_family_is_proxy": False,
                "execution_status": "scored",
                "candidate_label": "current_selected",
                "architecture_id": "kuijpers_hybrid_candidate",
                "partition_policy": "tomics_alloc_research",
                "mean_alloc_frac_fruit": 0.31,
                "mean_proxy_family_state_fraction": 0.1,
            },
            {
                "scenario_id": "research_current__profile__dataset_b",
                "allocation_lane_id": "research_current",
                "harvest_profile_id": "locked_research_selected_harvest_profile",
                "dataset_id": "dataset_b",
                "dataset_role": "measured_harvest",
                "promotion_eligible": True,
                "reference_only": False,
                "reporting_basis_in": "floor_area_g_m2",
                "reporting_basis_canonical": "floor_area_g_m2",
                "basis_normalization_resolved": True,
                "rmse_cumulative_offset": 1.1,
                "rmse_daily_increment": 0.5,
                "fruit_anchor_error": 0.06,
                "canopy_collapse_days": 0.0,
                "winner_stability_score": 1.0,
                "native_state_coverage": 0.85,
                "shared_tdvs_proxy_fraction": 0.15,
                "family_separability_score": 0.7,
                "any_all_zero_harvest_series": False,
                "dropped_nonharvested_mass_g_m2": 0.0,
                "offplant_with_positive_mass_flag": False,
                "runtime_complete_semantics": RUNTIME_COMPLETE_SEMANTICS,
                "selected_family_label": "locked",
                "selected_family_is_native": True,
                "selected_family_is_proxy": False,
                "execution_status": "scored",
                "candidate_label": "current_selected",
                "architecture_id": "kuijpers_hybrid_candidate",
                "partition_policy": "tomics_alloc_research",
                "mean_alloc_frac_fruit": 0.32,
                "mean_proxy_family_state_fraction": 0.15,
            },
            {
                "scenario_id": "raw_reference_thorp__profile__dataset_a",
                "allocation_lane_id": "raw_reference_thorp",
                "harvest_profile_id": "locked_research_selected_harvest_profile",
                "dataset_id": "dataset_a",
                "dataset_role": "measured_harvest",
                "promotion_eligible": False,
                "reference_only": True,
                "reporting_basis_in": "floor_area_g_m2",
                "reporting_basis_canonical": "floor_area_g_m2",
                "basis_normalization_resolved": True,
                "rmse_cumulative_offset": 0.8,
                "rmse_daily_increment": 0.3,
                "fruit_anchor_error": 0.2,
                "canopy_collapse_days": 0.0,
                "winner_stability_score": 1.0,
                "native_state_coverage": 0.8,
                "shared_tdvs_proxy_fraction": 0.1,
                "family_separability_score": 0.7,
                "any_all_zero_harvest_series": False,
                "dropped_nonharvested_mass_g_m2": 0.0,
                "offplant_with_positive_mass_flag": False,
                "runtime_complete_semantics": RUNTIME_COMPLETE_SEMANTICS,
                "selected_family_label": "locked",
                "selected_family_is_native": True,
                "selected_family_is_proxy": False,
                "execution_status": "scored",
                "candidate_label": "shipped_tomics",
                "architecture_id": "raw_thorp_like_control",
                "partition_policy": "thorp_fruit_veg",
                "mean_alloc_frac_fruit": 0.28,
                "mean_proxy_family_state_fraction": 0.2,
            },
            {
                "scenario_id": "research_promoted__profile__dataset_a",
                "allocation_lane_id": "research_promoted",
                "harvest_profile_id": "locked_research_selected_harvest_profile",
                "dataset_id": "dataset_a",
                "dataset_role": "measured_harvest",
                "promotion_eligible": True,
                "reference_only": False,
                "reporting_basis_in": "g_per_plant",
                "reporting_basis_canonical": "floor_area_g_m2",
                "basis_normalization_resolved": False,
                "rmse_cumulative_offset": 0.6,
                "rmse_daily_increment": 0.2,
                "fruit_anchor_error": 0.04,
                "canopy_collapse_days": 0.0,
                "winner_stability_score": 1.0,
                "native_state_coverage": 0.9,
                "shared_tdvs_proxy_fraction": 0.1,
                "family_separability_score": 0.8,
                "any_all_zero_harvest_series": False,
                "dropped_nonharvested_mass_g_m2": 0.0,
                "offplant_with_positive_mass_flag": False,
                "runtime_complete_semantics": RUNTIME_COMPLETE_SEMANTICS,
                "selected_family_label": "locked",
                "selected_family_is_native": True,
                "selected_family_is_proxy": False,
                "execution_status": "scored",
                "candidate_label": "promoted_selected",
                "architecture_id": "constrained_full_plus_feedback__buffer_capacity_g_m2_12p0",
                "partition_policy": "tomics_promoted_research",
                "mean_alloc_frac_fruit": 0.33,
                "mean_proxy_family_state_fraction": 0.1,
            },
        ]
    )
    scorecard.to_csv(matrix_root / "lane_scorecard.csv", index=False)
    gate_config_path = _write_lane_matrix_gate_config(tmp_path, repo_root=_repo_root(), matrix_root=matrix_root)
    config = load_config(gate_config_path)

    result = run_lane_matrix_gate(config, repo_root=_repo_root(), config_path=gate_config_path)
    output_root = Path(result["output_root"])

    assert (output_root / "promotion_surface.csv").exists()
    assert (output_root / "diagnostic_surface.csv").exists()
    assert (output_root / "lane_gate_decision.json").exists()

    promotion_surface = pd.read_csv(output_root / "promotion_surface.csv")
    diagnostic_surface = pd.read_csv(output_root / "diagnostic_surface.csv")
    decision = json.loads((output_root / "lane_gate_decision.json").read_text(encoding="utf-8"))

    assert "raw_reference_thorp" in set(diagnostic_surface["allocation_lane_id"])
    assert "raw_reference_thorp" not in set(promotion_surface["allocation_lane_id"])
    assert "research_promoted" not in set(promotion_surface["allocation_lane_id"])
    assert decision["promotion_surface_path"].endswith("promotion_surface.csv")
    assert decision["diagnostic_surface_path"].endswith("diagnostic_surface.csv")


@pytest.mark.slow
def test_lane_matrix_runner_current_knu_smoke(tmp_path: Path) -> None:
    repo_root = _repo_root()
    current_vs_promoted_config = write_minimal_knu_config(tmp_path, repo_root=repo_root, mode="both")
    current_vs_promoted_result = run_current_vs_promoted_factorial(config_path=current_vs_promoted_config, mode="both")
    extended_forcing_path = write_sampled_knu_forcing(tmp_path, sample_every_rows=360, min_days=14)
    extended_yield_path = write_sampled_knu_yield_fixture(tmp_path, min_days=14)
    harvest_factorial_config = write_minimal_knu_harvest_factorial_config(
        tmp_path,
        repo_root=repo_root,
        current_vs_promoted_config=current_vs_promoted_config,
        forcing_path=extended_forcing_path,
        yield_path=extended_yield_path,
    )
    harvest_factorial_cfg = load_config(harvest_factorial_config)
    harvest_factorial_result = run_harvest_family_factorial(
        harvest_factorial_cfg,
        repo_root=repo_root,
        config_path=harvest_factorial_config,
    )

    lane_matrix_config_path = _write_lane_matrix_config(
        tmp_path,
        repo_root=repo_root,
        current_vs_promoted_config=current_vs_promoted_config,
        current_output_root=Path(current_vs_promoted_result["current"]["output_root"]),
        promoted_output_root=Path(current_vs_promoted_result["promoted"]["output_root"]),
        selected_harvest_family_path=Path(harvest_factorial_result["output_root"]) / "selected_harvest_family.json",
        forcing_path=extended_forcing_path,
        yield_path=extended_yield_path,
    )
    lane_matrix_config = load_config(lane_matrix_config_path)
    _, reference_meta = load_harvest_candidates(
        config=lane_matrix_config,
        repo_root=repo_root,
        config_path=lane_matrix_config_path,
    )
    base_config = load_harvest_base_config(reference_meta)
    assert base_config["pipeline"]["model"] == "tomato_legacy"

    lane_matrix_result = run_lane_matrix(
        lane_matrix_config,
        repo_root=repo_root,
        config_path=lane_matrix_config_path,
    )
    output_root = Path(lane_matrix_result["output_root"])
    assert (output_root / "matrix_spec.json").exists()
    assert (output_root / "resolved_matrix_spec.json").exists()
    assert (output_root / "scenario_index.csv").exists()
    assert (output_root / "lane_scorecard.csv").exists()
    assert (output_root / "dataset_role_summary.csv").exists()

    lane_scorecard = pd.read_csv(output_root / "lane_scorecard.csv")
    assert {"legacy_sink_baseline", "incumbent_current", "research_current"}.issubset(
        set(lane_scorecard["allocation_lane_id"])
    )
    locked_rows = lane_scorecard.loc[
        lane_scorecard["harvest_profile_id"].eq("locked_research_selected_harvest_profile")
        & lane_scorecard["allocation_lane_id"].isin(["incumbent_current", "research_current"])
    ].copy()
    assert not locked_rows.empty
    assert set(locked_rows["reporting_basis_canonical"]) == {"floor_area_g_m2"}
    assert locked_rows["runtime_complete_semantics"].eq(RUNTIME_COMPLETE_SEMANTICS).all()

    gate_config_path = _write_lane_matrix_gate_config(tmp_path, repo_root=repo_root, matrix_root=output_root)
    gate_config = load_config(gate_config_path)
    gate_result = run_lane_matrix_gate(gate_config, repo_root=repo_root, config_path=gate_config_path)
    gate_root = Path(gate_result["output_root"])
    assert (gate_root / "promotion_surface.csv").exists()
    assert (gate_root / "diagnostic_surface.csv").exists()
    assert (gate_root / "lane_gate_decision.json").exists()


@pytest.mark.slow
def test_lane_matrix_runner_supports_multidataset_mode(tmp_path: Path) -> None:
    repo_root = _repo_root()
    current_vs_promoted_config = write_minimal_knu_config(tmp_path, repo_root=repo_root, mode="both")
    current_vs_promoted_result = run_current_vs_promoted_factorial(config_path=current_vs_promoted_config, mode="both")
    extended_forcing_path = write_sampled_knu_forcing(tmp_path, sample_every_rows=360, min_days=14)
    extended_yield_path = write_sampled_knu_yield_fixture(tmp_path, min_days=14)
    yield_dates = pd.to_datetime(pd.read_csv(extended_yield_path)["Date"], errors="raise").dt.normalize()
    validation_start = str(yield_dates.min().date())
    validation_end = str(yield_dates.max().date())
    forcing_copy = tmp_path / "KNU_Tomato_Env_sampled_copy.csv"
    forcing_copy.write_text(extended_forcing_path.read_text(encoding="utf-8"), encoding="utf-8")
    yield_copy = tmp_path / "tomato_validation_data_yield_sampled_copy.csv"
    yield_copy.write_text(extended_yield_path.read_text(encoding="utf-8"), encoding="utf-8")
    harvest_factorial_config = write_minimal_knu_harvest_factorial_config(
        tmp_path,
        repo_root=repo_root,
        current_vs_promoted_config=current_vs_promoted_config,
        forcing_path=extended_forcing_path,
        yield_path=extended_yield_path,
    )
    harvest_factorial_result = run_harvest_family_factorial(
        load_config(harvest_factorial_config),
        repo_root=repo_root,
        config_path=harvest_factorial_config,
    )
    lane_matrix_config_path = _write_lane_matrix_config(
        tmp_path,
        repo_root=repo_root,
        current_vs_promoted_config=current_vs_promoted_config,
        current_output_root=Path(current_vs_promoted_result["current"]["output_root"]),
        promoted_output_root=Path(current_vs_promoted_result["promoted"]["output_root"]),
        selected_harvest_family_path=Path(harvest_factorial_result["output_root"]) / "selected_harvest_family.json",
        forcing_path=extended_forcing_path,
        yield_path=extended_yield_path,
        dataset_items=[
            {
                "dataset_id": "knu_actual",
                "dataset_kind": "knu_measured_harvest",
                "display_name": "KNU actual",
                "forcing_path": str(extended_forcing_path),
                "observed_harvest_path": str(extended_yield_path),
                "validation_start": validation_start,
                "validation_end": validation_end,
                "cultivar": "unknown",
                "greenhouse": "KNU",
                "season": "window_a",
                "basis": {"reporting_basis": "floor_area_g_m2", "plants_per_m2": 1.836091},
                "observation": {
                    "date_column": "Date",
                    "measured_cumulative_column": "Measured_Cumulative_Total_Fruit_DW (g/m^2)",
                    "estimated_cumulative_column": "Estimated_Cumulative_Total_Fruit_DW (g/m^2)",
                    "measured_semantics": "cumulative_harvested_fruit_dry_weight_floor_area",
                },
                "sanitized_fixture": {
                    "forcing_fixture_path": str(extended_forcing_path),
                    "observed_harvest_fixture_path": str(extended_yield_path),
                },
                "notes": {"dataset_role_hint": "measured_harvest"},
            },
            {
                "dataset_id": "knu_actual_copy",
                "dataset_kind": "knu_measured_harvest",
                "display_name": "KNU actual copy",
                "forcing_path": str(forcing_copy),
                "observed_harvest_path": str(yield_copy),
                "validation_start": validation_start,
                "validation_end": validation_end,
                "cultivar": "unknown",
                "greenhouse": "KNU",
                "season": "window_b",
                "basis": {"reporting_basis": "floor_area_g_m2", "plants_per_m2": 1.836091},
                "observation": {
                    "date_column": "Date",
                    "measured_cumulative_column": "Measured_Cumulative_Total_Fruit_DW (g/m^2)",
                    "estimated_cumulative_column": "Estimated_Cumulative_Total_Fruit_DW (g/m^2)",
                    "measured_semantics": "cumulative_harvested_fruit_dry_weight_floor_area",
                },
                "sanitized_fixture": {
                    "forcing_fixture_path": str(forcing_copy),
                    "observed_harvest_fixture_path": str(yield_copy),
                },
                "notes": {"dataset_role_hint": "measured_harvest"},
            },
        ],
    )
    lane_matrix_result = run_lane_matrix(
        load_config(lane_matrix_config_path),
        repo_root=repo_root,
        config_path=lane_matrix_config_path,
    )
    output_root = Path(lane_matrix_result["output_root"])
    lane_scorecard = pd.read_csv(output_root / "lane_scorecard.csv")

    assert {"knu_actual", "knu_actual_copy"} <= set(lane_scorecard["dataset_id"])
