from __future__ import annotations

from pathlib import Path

import pandas as pd


def latent_config(output_root: str | Path = "out") -> dict:
    return {
        "paths": {"repo_root": "."},
        "tomics_haf": {
            "observer_feature_frame": "feature.csv",
            "observer_metadata": "metadata.json",
            "output_root": str(output_root),
        },
        "latent_allocation": {
            "require_production_observer_export": True,
            "require_row_cap_absent": True,
            "require_radiation_defined_daynight": True,
            "prior_families": [
                "legacy_tomato_prior",
                "thorp_bounded_prior",
                "tomato_constrained_thorp_prior",
            ],
            "inference_method": "prior_weighted_softmax",
            "softmax_beta": 1.0,
            "low_pass_memory_enabled": True,
            "low_pass_alpha": 0.35,
            "biological_floors": {"fruit": 0.05, "leaf": 0.12, "stem": 0.08, "root": 0.02},
            "biological_caps": {"fruit": 0.85, "leaf": 0.55, "stem": 0.45, "root": 0.25, "wet_root": 0.12},
            "lai": {
                "target_lai": 3.0,
                "lai_available": False,
                "lai_proxy_allowed": True,
                "lai_proxy_source": "radiation_source_capacity_and_leaf_temperature_observer",
                "lai_protection_enabled": True,
            },
            "thorp": {
                "enabled_as_raw_allocator": False,
                "enabled_as_bounded_prior": True,
                "enabled_as_diagnostic_comparator": True,
                "root_hydraulic_correction_max_abs": 0.08,
                "vegetative_redistribution_only": True,
                "fruit_gate_override_allowed": False,
            },
            "stress_gates": {
                "root_stress_gate_enabled": True,
                "rzi_activation_threshold": 0.15,
                "wet_rzi_threshold": 0.05,
                "apparent_conductance_required_for_hydraulic_signal": False,
            },
        },
    }


def observer_metadata(*, row_cap_applied: bool = False) -> dict:
    return {
        "production_ready_for_latent_allocation": not row_cap_applied,
        "production_export_completed": not row_cap_applied,
        "row_cap_applied": row_cap_applied,
        "chunk_aggregation_used": True,
        "fixed_clock_daynight_primary": False,
        "radiation_column_used": "env_inside_radiation_wm2",
        "radiation_daynight_primary_source": "dataset1",
        "dataset1_radiation_directly_usable": True,
        "event_bridged_ET_calibration_status": "uncalibrated_no_daily_total",
        "Dataset3_mapping_confidence": "direct_loadcell_no_date",
        "apparent_canopy_conductance_available": True,
        "fruit_diameter_p_values_allowed": False,
        "fruit_diameter_allocation_calibration_target": False,
        "fruit_diameter_model_promotion_target": False,
    }


def feature_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "date": ["2025-12-14", "2025-12-15", "2025-12-14", "2025-12-15"],
            "loadcell_id": [1, 1, 4, 4],
            "treatment": ["Control", "Control", "Drought", "Drought"],
            "threshold_w_m2": [0, 0, 0, 0],
            "radiation_day_ET_g": [120.0, 118.0, 80.0, 75.0],
            "radiation_night_ET_g": [25.0, 24.0, 18.0, 17.0],
            "radiation_total_ET_g": [145.0, 142.0, 98.0, 92.0],
            "day_fraction_ET": [0.82, 0.83, 0.81, 0.82],
            "night_fraction_ET": [0.18, 0.17, 0.19, 0.18],
            "day_radiation_integral_MJ_m2": [12.0, 11.5, 12.0, 11.5],
            "day_radiation_mean_wm2": [300.0, 290.0, 300.0, 290.0],
            "RZI_main": [0.02, 0.03, 0.35, 0.40],
            "RZI_theta_paired": [0.0, 0.0, 0.35, 0.40],
            "RZI_theta_group": [0.0, 0.0, 0.30, 0.32],
            "tensiometer_available": [True, True, True, True],
            "tensiometer_coverage_fraction": [1.0, 1.0, 1.0, 1.0],
            "apparent_canopy_conductance": [60.0, 59.0, 40.0, 38.0],
            "apparent_canopy_conductance_available": [True, True, True, True],
            "day_vpd_kpa_mean": [2.0, 2.0, 2.2, 2.2],
            "source_proxy_MJ_CO2_T": [12.0, 11.0, 10.0, 9.5],
            "source_proxy_MJ_CO2_T_available": [True, True, True, True],
            "leaf_temp_lc4_radiation_day_mean_c": [26.0, 26.2, 28.0, 28.3],
            "leaf_temp_lc1_radiation_day_mean_c": [25.0, 25.2, 25.0, 25.2],
            "delta_leaf_temp_lc4_minus_lc1_radiation_day_mean_c": [1.0, 1.0, 3.0, 3.1],
            "sensor_column": ["Fruit2Diameter_Avg", "Fruit2Diameter_Avg", "Fruit1Diameter_Avg", "Fruit1Diameter_Avg"],
            "radiation_day_net_mm": [0.10, 0.12, 0.08, 0.07],
            "stable_flag": [True, True, True, True],
            "stem_diameter_mean": [9.0, 9.1, 8.5, 8.4],
            "Dataset3_mapping_confidence": ["direct_loadcell_no_date"] * 4,
            "direct_partition_observation_available": [False] * 4,
            "allocation_validation_basis": ["indirect_observer_features_only"] * 4,
            "LAI_available": [False] * 4,
            "harvest_yield_available": [False] * 4,
            "fruit_diameter_p_values_allowed": [False] * 4,
            "fruit_diameter_allocation_calibration_target": [False] * 4,
        }
    )
