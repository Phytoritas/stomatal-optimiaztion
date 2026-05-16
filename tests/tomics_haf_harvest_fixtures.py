from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd


def write_synthetic_haf_harvest_inputs(tmp_path: Path) -> dict[str, Path]:
    observer_path = tmp_path / "observer_feature_frame.csv"
    observer_metadata_path = tmp_path / "observer_metadata.json"
    latent_path = tmp_path / "latent_allocation_posteriors.csv"
    latent_metadata_path = tmp_path / "latent_allocation_metadata.json"
    output_root = tmp_path / "harvest-family"

    rows = []
    for loadcell_id, treatment in [(1, "Control"), (4, "Drought")]:
        cumulative = 0.0
        for day, daily in enumerate([0.0, 100.0, 140.0], start=1):
            cumulative += daily
            rows.append(
                {
                    "date": f"2025-11-0{day}",
                    "loadcell_id": loadcell_id,
                    "treatment": treatment,
                    "threshold_w_m2": 0,
                    "fresh_yield_available": True,
                    "fresh_yield_source": "synthetic_legacy_v1_3",
                    "harvest_yield_available": True,
                    "dry_yield_available": True,
                    "dry_yield_source": "fresh_yield_times_canonical_DMC_0p056",
                    "loadcell_daily_yield_g": daily,
                    "loadcell_cumulative_yield_g": cumulative,
                    "observed_fruit_FW_g_loadcell": cumulative,
                    "canonical_fruit_DMC_fraction": 0.056,
                    "fruit_DMC_fraction": 0.056,
                    "default_fruit_dry_matter_content": 0.056,
                    "DMC_fixed_for_2025_2C": True,
                    "DMC_sensitivity_enabled": False,
                    "dry_yield_is_dmc_estimated": True,
                    "direct_dry_yield_measured": False,
                    "legacy_yield_bridge_provenance": "legacy_v1_3_derived_output",
                }
            )
    pd.DataFrame(rows).to_csv(observer_path, index=False)

    observer_metadata = {
        "season_id": "2025_2C",
        "radiation_daynight_primary_source": "dataset1",
        "radiation_column_used": "env_inside_radiation_wm2",
        "fixed_clock_daynight_primary": False,
        "clock_06_18_used_only_for_compatibility": True,
        "event_bridged_ET_calibration_status": "calibrated_to_legacy_daily_event_total",
        "event_bridged_ET_calibration_provenance": "legacy_v1_3_derived_output",
        "RZI_main_available": True,
        "RZI_main_source": "theta_paired_lc4_vs_lc1",
        "RZI_control_reference_source": "dataset1_moisture_lc1_lc6",
        "fresh_yield_available": True,
        "dry_yield_available": True,
        "dry_yield_is_dmc_estimated": True,
        "direct_dry_yield_measured": False,
        "dry_yield_source": "fresh_yield_times_canonical_DMC_0p056",
        "canonical_fruit_DMC_fraction": 0.056,
        "fruit_DMC_fraction": 0.056,
        "default_fruit_dry_matter_content": 0.056,
        "DMC_fixed_for_2025_2C": True,
        "DMC_sensitivity_enabled": False,
        "DMC_sensitivity_values": [],
        "deprecated_previous_default_fruit_DMC_fraction": 0.065,
        "legacy_yield_bridge_provenance": "legacy_v1_3_derived_output",
    }
    observer_metadata_path.write_text(json.dumps(observer_metadata), encoding="utf-8")

    latent_rows = []
    for prior in [
        "legacy_tomato_prior",
        "thorp_bounded_prior",
        "tomato_constrained_thorp_prior",
    ]:
        for loadcell_id, treatment in [(1, "Control"), (4, "Drought")]:
            for day in range(1, 4):
                latent_rows.append(
                    {
                        "date": f"2025-11-0{day}",
                        "loadcell_id": loadcell_id,
                        "treatment": treatment,
                        "prior_family": prior,
                        "inferred_u_fruit": 0.50 + 0.01 * day,
                        "latent_allocation_directly_validated": False,
                        "raw_THORP_allocator_used": False,
                    }
                )
    pd.DataFrame(latent_rows).to_csv(latent_path, index=False)
    latent_metadata = {
        "latent_allocation_ready": True,
        "latent_allocation_guardrails_passed": True,
        "canonical_fruit_DMC_fraction": 0.056,
        "DMC_fixed_for_2025_2C": True,
        "DMC_sensitivity_enabled": False,
        "dry_yield_is_dmc_estimated": True,
        "direct_dry_yield_measured": False,
        "raw_THORP_allocator_used": False,
    }
    latent_metadata_path.write_text(json.dumps(latent_metadata), encoding="utf-8")

    return {
        "observer": observer_path,
        "observer_metadata": observer_metadata_path,
        "latent": latent_path,
        "latent_metadata": latent_metadata_path,
        "output_root": output_root,
    }


def synthetic_haf_harvest_config(paths: dict[str, Path]) -> dict[str, Any]:
    return {
        "exp": {"name": "synthetic_haf_harvest"},
        "tomics_haf": {
            "season_id": "2025_2C",
            "observer_feature_frame": str(paths["observer"]),
            "observer_metadata": str(paths["observer_metadata"]),
            "latent_allocation_posteriors": str(paths["latent"]),
            "latent_allocation_metadata": str(paths["latent_metadata"]),
            "output_root": str(paths["output_root"]),
        },
        "harvest_family_factorial": {
            "mode": "staged",
            "run_HF0": True,
            "run_HF1": True,
            "run_HF2": True,
            "run_HF3": True,
            "run_HF4_budget_parity": True,
            "run_HF5_promotion_gate": False,
            "run_HF6_oracle_diagnostics": False,
            "incumbent": {
                "allocator_family": "shipped_tomics",
                "fruit_harvest_family": "tomsim_truss_incumbent",
                "leaf_harvest_family": "leaf_harvest_tomsim_legacy",
                "observation_operator": "fresh_to_dry_dmc_0p056",
            },
            "allocator_families": [
                "shipped_tomics",
                "source_only",
                "hydraulic_only",
                "allocation_only",
                "tomics_haf_latent_allocation_research",
            ],
            "latent_allocation_prior_families": [
                "legacy_tomato_prior",
                "thorp_bounded_prior",
                "tomato_constrained_thorp_prior",
            ],
            "fruit_harvest_families": [
                "tomsim_truss_incumbent",
                "tomgro_ageclass_mature_pool",
                "dekoning_fds_ripe",
                "vanthoor_boxcar_stageflow",
            ],
            "leaf_harvest_families": [
                "leaf_harvest_tomsim_legacy",
                "leaf_harvest_none",
                "leaf_harvest_max_lai",
                "leaf_harvest_vanthoor_mcleafhar",
            ],
            "always_include": {
                "fruit_harvest_families": [
                    "tomsim_truss_incumbent",
                    "dekoning_fds_ripe",
                ],
            },
            "parameter_grid": {
                "harvest_delay_days": [0, 1],
                "harvest_readiness_threshold": [0.95, 1.0],
                "vanthoor_boxcar_n_stages": [4, 5],
                "tomgro_mature_pool_age_class": ["last", "last_two"],
                "fdmc_mode": ["constant_0p056"],
            },
        },
        "promotion": {
            "run_final_promotion_gate": False,
            "single_dataset_promotion_allowed": False,
            "require_cross_dataset_for_promotion": True,
        },
    }
