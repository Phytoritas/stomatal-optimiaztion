from __future__ import annotations

from pathlib import Path

import pandas as pd
import yaml


def write_sampled_knu_forcing(tmp_path: Path, *, sample_every_rows: int = 360) -> Path:
    repo_root = Path(__file__).resolve().parents[1]
    fixture = repo_root / "tests" / "fixtures" / "knu_sanitized" / "KNU_Tomato_Env_fixture.csv"
    df = pd.read_csv(fixture).copy()
    stride = 1 if df.shape[0] <= sample_every_rows else max(sample_every_rows, 1)
    df = df.iloc[::stride].copy()
    out_path = tmp_path / "KNU_Tomato_Env_sampled.csv"
    df.to_csv(out_path, index=False)
    return out_path


def write_minimal_current_base_config(tmp_path: Path, *, repo_root: Path) -> Path:
    config = {
        "exp": {"name": "current_knu_test_base"},
        "pipeline": {
            "model": "tomato_legacy",
            "partition_policy": "tomics",
            "allocation_scheme": "4pool",
            "theta_substrate": 0.65,
            "fixed_lai": None,
            "partition_policy_params": {
                "wet_root_cap": 0.10,
                "dry_root_cap": 0.18,
                "lai_target_center": 2.75,
            },
        },
        "forcing": {
            "csv_path": str(repo_root / "data" / "forcing" / "tomics_tomato_example.csv"),
            "default_dt_s": 21600,
            "default_co2_ppm": 420,
        },
        "stage1": {
            "candidates": [
                {
                    "architecture_id": "shipped_default_tomics",
                    "partition_policy": "tomics",
                    "fruit_structure_mode": "tomsim_truss_cohort",
                    "fruit_partition_mode": "legacy_sink_exact",
                    "vegetative_demand_mode": "tomsim_constant_wholecrop",
                    "reserve_buffer_mode": "off",
                    "fruit_feedback_mode": "off",
                    "sla_mode": "derived_not_driver",
                    "maintenance_mode": "rgr_adjusted",
                    "canopy_governor_mode": "lai_band",
                    "root_representation_mode": "bounded_explicit_root",
                    "thorp_root_correction_mode": "bounded",
                    "temporal_coupling_mode": "daily_alloc",
                    "allocation_scheme": "4pool",
                    "wet_root_cap": 0.10,
                    "dry_root_cap": 0.18,
                    "lai_target_center": 2.75,
                    "leaf_fraction_of_shoot_base": 0.70,
                    "thorp_root_blend": 1.0,
                },
                {
                    "architecture_id": "kuijpers_hybrid_candidate",
                    "partition_policy": "tomics_alloc_research",
                    "fruit_structure_mode": "tomsim_truss_cohort",
                    "fruit_partition_mode": "legacy_sink_exact",
                    "vegetative_demand_mode": "dekoning_vegetative_unit",
                    "reserve_buffer_mode": "tomsim_storage_pool",
                    "fruit_feedback_mode": "off",
                    "sla_mode": "derived_not_driver",
                    "maintenance_mode": "buffer_linked",
                    "canopy_governor_mode": "lai_band_plus_leaf_floor",
                    "root_representation_mode": "bounded_explicit_root",
                    "thorp_root_correction_mode": "bounded_hysteretic",
                    "temporal_coupling_mode": "buffered_daily",
                    "allocation_scheme": "4pool",
                    "wet_root_cap": 0.10,
                    "dry_root_cap": 0.18,
                    "lai_target_center": 2.75,
                    "leaf_fraction_of_shoot_base": 0.72,
                    "thorp_root_blend": 1.0,
                    "storage_capacity_g_ch2o_m2": 15.0,
                    "storage_carryover_fraction": 0.8,
                },
            ]
        },
        "stage2": {
            "parameter_axes": {
                "wet_root_cap": [0.08, 0.10],
                "thorp_root_blend": [0.5, 1.0],
            }
        },
    }
    out_path = tmp_path / "current_base.yaml"
    out_path.write_text(yaml.safe_dump(config, sort_keys=False, allow_unicode=False), encoding="utf-8")
    return out_path


def write_minimal_knu_config(tmp_path: Path, *, repo_root: Path, mode: str = "both") -> Path:
    forcing_path = write_sampled_knu_forcing(tmp_path, sample_every_rows=360)
    current_base = write_minimal_current_base_config(tmp_path, repo_root=repo_root)
    yield_path = repo_root / "tests" / "fixtures" / "knu_sanitized" / "tomato_validation_data_yield_fixture.csv"
    config = {
        "exp": {"name": f"tomics_knu_{mode}_test"},
        "validation": {
            "forcing_csv_path": str(forcing_path),
            "yield_xlsx_path": str(yield_path),
            "prepared_output_root": str(tmp_path / "out" / "knu_longrun"),
            "resample_rule": "6h",
            "theta_proxy_mode": "bucket_irrigated",
            "theta_proxy_scenarios": ["moderate"],
            "calibration_end": "2024-08-19",
        },
        "current": {
            "base_config": str(current_base),
            "theta_proxy_scenarios": ["moderate"],
            "shortlist_count": 1,
            "wet_theta_threshold": 0.75,
            "canopy_lai_floor": 2.0,
            "leaf_fraction_floor": 0.18,
            "fruit_load_regimes": {"observed_baseline": 1.0},
        },
        "promoted": {
            "base_config": str(current_base),
            "theta_proxy_scenarios": ["moderate"],
            "shortlist_count": 1,
            "wet_theta_threshold": 0.75,
            "canopy_lai_floor": 2.0,
            "leaf_fraction_floor": 0.18,
            "fruit_load_regimes": {"observed_baseline": 1.0},
        },
        "paths": {
            "repo_root": str(repo_root),
            "current_output_root": str(tmp_path / "out" / "current"),
            "promoted_output_root": str(tmp_path / "out" / "promoted"),
            "comparison_output_root": str(tmp_path / "out" / "comparison"),
        },
        "plots": {
            "current_summary_plot_spec": "configs/plotkit/tomics/allocation_factorial_summary.yaml",
            "current_main_effects_plot_spec": "configs/plotkit/tomics/allocation_factorial_main_effects.yaml",
            "promoted_summary_plot_spec": "configs/plotkit/tomics/allocation_factorial_summary.yaml",
            "promoted_main_effects_plot_spec": "configs/plotkit/tomics/allocation_factorial_main_effects.yaml",
            "comparison_summary_plot_spec": "configs/plotkit/tomics/knu_current_vs_promoted_summary.yaml",
            "yield_fit_overlay_spec": "configs/plotkit/tomics/knu_yield_fit_overlay.yaml",
            "allocation_behavior_overlay_spec": "configs/plotkit/tomics/knu_allocation_behavior_overlay.yaml",
            "theta_proxy_diagnostics_spec": "configs/plotkit/tomics/knu_theta_proxy_diagnostics.yaml",
        },
    }
    out_path = tmp_path / f"knu_{mode}_config.yaml"
    out_path.write_text(yaml.safe_dump(config, sort_keys=False, allow_unicode=False), encoding="utf-8")
    return out_path


def write_minimal_knu_fairness_config(tmp_path: Path, *, repo_root: Path) -> Path:
    forcing_path = write_sampled_knu_forcing(tmp_path, sample_every_rows=360)
    current_base = write_minimal_current_base_config(tmp_path, repo_root=repo_root)
    yield_path = repo_root / "tests" / "fixtures" / "knu_sanitized" / "tomato_validation_data_yield_fixture.csv"
    contract_path = tmp_path / "knu_private_data_contract.yaml"
    contract_path.write_text(
        yaml.safe_dump(
            {
                "private_data_root_env": "PHYTORITAS_PRIVATE_DATA_ROOT",
                "private_data_root": "",
                "forcing_relative_path": "unused/KNU_Tomato_Env.CSV",
                "yield_relative_path": "unused/tomato_validation_data_yield_260222.xlsx",
                "reporting_basis": "floor_area_g_m2",
                "plants_per_m2": 1.836091,
                "parser_assumptions": {
                    "observation_semantics": "cumulative_harvested_fruit_dry_weight_floor_area",
                },
            },
            sort_keys=False,
            allow_unicode=False,
        ),
        encoding="utf-8",
    )
    config = {
        "exp": {"name": "tomics_knu_fairness_test"},
        "validation": {
            "forcing_csv_path": str(forcing_path),
            "yield_xlsx_path": str(yield_path),
            "private_data_contract_path": str(contract_path),
            "prepared_output_root": str(tmp_path / "out" / "knu_longrun"),
            "resample_rule": "6h",
            "theta_proxy_mode": "bucket_irrigated",
            "theta_proxy_scenarios": ["dry", "moderate", "wet"],
            "calibration_end": "2024-08-10",
        },
        "selection": {
            "current_output_root": str(tmp_path / "out" / "current"),
            "promoted_output_root": str(tmp_path / "out" / "promoted"),
        },
        "calibration": {
            "base_config": str(current_base),
            "output_root": str(tmp_path / "out" / "calibration"),
            "wet_theta_threshold": 0.75,
            "canopy_lai_floor": 2.0,
            "leaf_fraction_floor": 0.18,
            "rolling_window_days": 2,
            "shared_parameter_grid": {
                "fruit_load_multiplier": [0.9, 1.0],
                "lai_target_center": [2.5, 2.75],
            },
            "holdout_overlay_spec": "configs/plotkit/tomics/knu_yield_fit_overlay.yaml",
            "daily_increment_overlay_spec": "configs/plotkit/tomics/knu_daily_increment_overlay.yaml",
        },
        "observation_eval": {
            "output_root": str(tmp_path / "out" / "observation_eval"),
            "cumulative_overlay_spec": "configs/plotkit/tomics/knu_cumulative_overlay.yaml",
            "daily_overlay_spec": "configs/plotkit/tomics/knu_daily_increment_overlay.yaml",
        },
        "state_reconstruction": {
            "output_root": str(tmp_path / "out" / "state_reconstruction"),
            "modes": ["minimal_scalar_init", "cohort_aware_init", "buffer_aware_init"],
            "overlay_spec": "configs/plotkit/tomics/knu_cumulative_overlay.yaml",
        },
        "rootzone_reconstruction": {
            "output_root": str(tmp_path / "out" / "rootzone"),
            "theta_proxy_mode": "bucket_irrigated",
            "scenario_ids": ["dry", "moderate", "wet"],
            "theta_min_hard": 0.40,
            "theta_max_hard": 0.85,
            "overlay_spec": "configs/plotkit/tomics/knu_theta_proxy_diagnostics.yaml",
        },
        "identifiability": {
            "fruit_load_multiplier_delta": 0.05,
            "lai_target_center_delta": 0.25,
        },
        "promotion_gate": {
            "output_root": str(tmp_path / "out" / "promotion_gate"),
            "material_rmse_margin": 0.5,
            "material_rmse_fraction": 0.02,
            "wet_root_penalty_max": 0.05,
            "parameter_instability_score_max": 0.50,
            "promotion_overlay_spec": "configs/plotkit/tomics/knu_yield_fit_overlay.yaml",
        },
    }
    out_path = tmp_path / "knu_fairness_config.yaml"
    out_path.write_text(yaml.safe_dump(config, sort_keys=False, allow_unicode=False), encoding="utf-8")
    return out_path


def write_minimal_fairness_config(
    tmp_path: Path,
    *,
    repo_root: Path,
    filename: str,
    section_name: str,
    section_payload: dict[str, object] | None = None,
) -> Path:
    current_vs_promoted_config = write_minimal_knu_config(tmp_path, repo_root=repo_root, mode="both")
    forcing_path = write_sampled_knu_forcing(tmp_path, sample_every_rows=360)
    yield_path = repo_root / "tests" / "fixtures" / "knu_sanitized" / "tomato_validation_data_yield_fixture.csv"
    config = {
        "exp": {"name": Path(filename).stem},
        "paths": {
            "repo_root": str(repo_root),
        },
        "validation": {
            "forcing_csv_path": str(forcing_path),
            "yield_xlsx_path": str(yield_path),
            "prepared_output_root": str(tmp_path / "out" / "knu_longrun"),
            "resample_rule": "6h",
            "theta_proxy_mode": "bucket_irrigated",
            "theta_proxy_scenarios": ["dry", "moderate", "wet"],
            "calibration_end": "2024-08-19",
        },
        "reference": {
            "current_vs_promoted_config": str(current_vs_promoted_config),
            "current_output_root": str(tmp_path / "out" / "current"),
            "promoted_output_root": str(tmp_path / "out" / "promoted"),
        },
        section_name: {
            "output_root": str(tmp_path / "out" / section_name),
            **(section_payload or {}),
        },
        "calibration": {
            "output_root": str(tmp_path / "out" / "calibration"),
            "wet_theta_threshold": 0.75,
            "canopy_lai_floor": 2.0,
            "leaf_fraction_floor": 0.18,
        },
        "promotion_gate": {
            "output_root": str(tmp_path / "out" / "promotion_gate"),
        },
        "plots": {
            "yield_fit_overlay_spec": "configs/plotkit/tomics/knu_yield_fit_overlay.yaml",
            "theta_proxy_diagnostics_spec": "configs/plotkit/tomics/knu_theta_proxy_diagnostics.yaml",
        },
    }
    out_path = tmp_path / filename
    out_path.write_text(yaml.safe_dump(config, sort_keys=False, allow_unicode=False), encoding="utf-8")
    return out_path
