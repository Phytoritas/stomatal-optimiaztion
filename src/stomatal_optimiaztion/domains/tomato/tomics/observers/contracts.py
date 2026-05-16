from __future__ import annotations

from pathlib import Path
from typing import Any

SEASON_ID = "2025_2C"
RAW_FILENAME_NOTE = (
    "Some raw filenames contain 2026_2; biological evaluation season is "
    "user-defined as 2025 second cropping cycle."
)

OBSERVER_PIPELINE_VERSION = "tomics-haf-2025-2c-observer-v1"

RADIATION_THRESHOLDS_W_M2: tuple[int, ...] = (0, 1, 5, 10)
MAIN_RADIATION_THRESHOLD_W_M2 = 0
RADIATION_COLUMN_USED = "env_inside_radiation_wm2"
RADIATION_PRIMARY_SOURCE = "dataset1"

DEFAULT_FRUIT_DRY_MATTER_CONTENT = 0.065
DMC_SENSITIVITY: tuple[float, ...] = (0.040, 0.052, 0.056, 0.060, 0.065, 0.080)

RAW_INPUT_FILENAMES = {
    "fruit_leaf_temperature_solar_raw_dat": "2026_2작기_토마토_엽온_과실직경.dat",
    "dataset1": "dataset1_loadcell_1_6_daily_ec_moisture_yield_env.parquet",
    "dataset2": "dataset2_loadcell_4_5_daily_ec_moisture_tensiometer.parquet",
    "dataset3": "dataset3_individual_stem_diameter_flower_height_flowering_date.parquet",
}

DATASET1_COLUMN_CANDIDATES: tuple[str, ...] = (
    "timestamp",
    "date",
    "loadcell_id",
    "sample_id",
    "treatment",
    "loadcell_weight_kg",
    "env_inside_radiation_wm2",
    "env_vpd_kpa",
    "env_air_temperature_c",
    "env_co2_ppm",
    "moisture_percent",
    "ec_ds",
)

DATASET2_COLUMN_CANDIDATES: tuple[str, ...] = (
    "timestamp",
    "date",
    "loadcell_id",
    "sample_id",
    "treatment",
    "loadcell_weight_kg",
    "moisture_percent",
    "ec_ds",
    "tensiometer_hp",
)

DATASET3_COLUMN_CANDIDATES: tuple[str, ...] = (
    "season",
    "sample_id",
    "loadcell_id",
    "treatment",
    "flower_cluster_no",
    "flowering_date",
    "stem_diameter",
    "flower_cluster_height",
    "has_flowering_date",
    "has_stem_diameter",
    "has_flower_cluster_height",
)

OUTPUT_FILENAMES = {
    "fruit_leaf_timeseries_qc": "2025_2c_fruit_leaf_timeseries_qc.csv",
    "sensor_qc_report": "2025_2c_sensor_qc_report.csv",
    "radiation_photoperiod": "radiation_photoperiod_by_date_all_thresholds.csv",
    "event_intervals": "radiation_daynight_10min_event_bridged_intervals.csv",
    "event_daily_all_thresholds": "radiation_daynight_event_bridged_daily_all_thresholds.csv",
    "event_daily_main_0w": "radiation_daynight_event_bridged_daily_main_0W.csv",
    "event_daily_wide_main_0w": "radiation_daynight_daily_wide_main_0W.csv",
    "fruit_leaf_radiation_windows": "2025_2c_fruit_leaf_radiation_windows.csv",
    "fruit_leaf_clock_windows": "2025_2c_fruit_leaf_clock_compat_windows.csv",
    "fruit_leaf_loadcell_bridge": "2025_2c_fruit_leaf_loadcell_bridge.csv",
    "rootzone_indices": "2025_2c_rootzone_indices.csv",
    "dataset3_bridge": "2025_2c_dataset3_growth_phenology_bridge.csv",
    "observer_feature_frame": "2025_2c_tomics_haf_observer_feature_frame.csv",
    "metadata": "2025_2c_tomics_haf_metadata.json",
    "chunk_manifest": "observer_production_chunk_manifest.csv",
    "production_export_summary": "observer_production_export_summary.md",
}


def resolve_repo_path(repo_root: Path, value: str | Path) -> Path:
    candidate = Path(value)
    if candidate.is_absolute():
        return candidate
    return (repo_root / candidate).resolve()


def base_metadata() -> dict[str, Any]:
    return {
        "season_id": SEASON_ID,
        "raw_filename_note": RAW_FILENAME_NOTE,
        "observer_pipeline_version": OBSERVER_PIPELINE_VERSION,
        "radiation_daynight_primary_source": RADIATION_PRIMARY_SOURCE,
        "radiation_column_used": RADIATION_COLUMN_USED,
        "radiation_thresholds_tested": list(RADIATION_THRESHOLDS_W_M2),
        "main_radiation_threshold_wm2": MAIN_RADIATION_THRESHOLD_W_M2,
        "fixed_clock_daynight_primary": False,
        "clock_06_18_used_only_for_compatibility": True,
        "dataset1_radiation_directly_usable": True,
        "dataset1_radiation_grain": "high_frequency_10min_or_finer",
        "fallback_required": False,
        "fallback_source_if_required": None,
        "raw_dat_solar_rad_fallback_verified": True,
        "VPD_available": True,
        "apparent_canopy_conductance_available": True,
        "LAI_available": False,
        "fresh_yield_available": False,
        "dry_yield_available": False,
        "DMC_conversion_performed": False,
        "default_fruit_dry_matter_content": DEFAULT_FRUIT_DRY_MATTER_CONTENT,
        "dmc_sensitivity": list(DMC_SENSITIVITY),
        "biological_replication": False,
        "fruit_diameter_sensor_level_only": True,
        "fruit_diameter_treatment_endpoint": False,
        "fruit_diameter_p_values_allowed": False,
        "fruit_diameter_allocation_calibration_target": False,
        "fruit_diameter_model_promotion_target": False,
        "fixed_clock_outputs_compatibility_only": True,
        "shipped_TOMICS_incumbent_changed": False,
        "latent_allocation_inference_run": False,
        "harvest_family_factorial_run": False,
        "promotion_gate_run": False,
    }
