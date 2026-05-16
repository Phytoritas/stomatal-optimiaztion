from __future__ import annotations

import numpy as np
import pandas as pd

from stomatal_optimiaztion.domains.tomato.tomics.observers.contracts import (
    CANONICAL_2025_2C_FRUIT_DMC,
    DEFAULT_FRUIT_DRY_MATTER_CONTENT,
    DEPRECATED_PREVIOUS_DEFAULT_FRUIT_DMC,
    HAF_2025_2C_LOADCELL_FLOOR_AREA_M2,
    MAIN_RADIATION_THRESHOLD_W_M2,
    RADIATION_COLUMN_USED,
)


def _merge_optional(base: pd.DataFrame, other: pd.DataFrame, keys: list[str]) -> pd.DataFrame:
    if other is None or other.empty:
        return base
    merge_keys = [key for key in keys if key in base.columns and key in other.columns]
    if not merge_keys:
        return base
    return base.merge(other, on=merge_keys, how="left")


def build_observer_feature_frame(
    *,
    daily_et_wide: pd.DataFrame,
    radiation_daily: pd.DataFrame | None = None,
    rootzone_indices: pd.DataFrame | None = None,
    fruit_windows: pd.DataFrame | None = None,
    leaf_windows: pd.DataFrame | None = None,
    dataset3_bridge: pd.DataFrame | None = None,
    radiation_source_used: str = "dataset1",
    radiation_column_used: str = RADIATION_COLUMN_USED,
) -> pd.DataFrame:
    if daily_et_wide is not None and not daily_et_wide.empty:
        base = daily_et_wide.copy()
    elif radiation_daily is not None and not radiation_daily.empty:
        base = radiation_daily[radiation_daily["threshold_w_m2"].eq(float(MAIN_RADIATION_THRESHOLD_W_M2))].copy()
    else:
        base = pd.DataFrame(columns=["date", "loadcell_id", "treatment", "threshold_w_m2"])

    if "threshold_w_m2" not in base.columns:
        base["threshold_w_m2"] = float(MAIN_RADIATION_THRESHOLD_W_M2)

    if radiation_daily is not None and not radiation_daily.empty:
        radiation_main = radiation_daily[radiation_daily["threshold_w_m2"].eq(float(MAIN_RADIATION_THRESHOLD_W_M2))].copy()
        keep = [
            column
            for column in radiation_main.columns
            if column
            in {
                "date",
                "loadcell_id",
                "treatment",
                "threshold_w_m2",
                "day_interval_count",
                "night_interval_count",
                "day_radiation_integral_MJ_m2",
                "night_radiation_integral_MJ_m2",
                "day_radiation_mean_wm2",
                "night_radiation_mean_wm2",
                "source_proxy_MJ_CO2_T",
                "source_proxy_MJ_CO2_T_available",
                "day_vpd_kpa_mean",
            }
        ]
        base = _merge_optional(base, radiation_main[keep], ["date", "loadcell_id", "treatment", "threshold_w_m2"])

    base = _merge_optional(
        base,
        rootzone_indices if rootzone_indices is not None else pd.DataFrame(),
        ["date", "loadcell_id", "treatment"],
    )
    if leaf_windows is not None and not leaf_windows.empty:
        leaf_main = leaf_windows[leaf_windows["threshold_w_m2"].eq(float(MAIN_RADIATION_THRESHOLD_W_M2))].copy()
        base = _merge_optional(base, leaf_main, ["date", "threshold_w_m2"])
    if fruit_windows is not None and not fruit_windows.empty:
        fruit_main = fruit_windows[fruit_windows["threshold_w_m2"].eq(float(MAIN_RADIATION_THRESHOLD_W_M2))].copy()
        base = _merge_optional(base, fruit_main, ["date", "loadcell_id", "treatment", "threshold_w_m2"])
    if dataset3_bridge is not None and not dataset3_bridge.empty:
        if "date" in dataset3_bridge.columns:
            base = _merge_optional(base, dataset3_bridge, ["date", "loadcell_id", "treatment"])
        elif {"loadcell_id", "treatment"}.issubset(dataset3_bridge.columns):
            base = _merge_optional(base, dataset3_bridge, ["loadcell_id", "treatment"])
        elif "treatment" in dataset3_bridge.columns:
            base = _merge_optional(base, dataset3_bridge, ["treatment"])

    base["biological_replication"] = False
    base["sensor_level_only"] = True
    base["fruit_mapping_status"] = "provisional"
    base["radiation_source_used"] = radiation_source_used
    base["radiation_column_used"] = radiation_column_used
    base["fixed_clock_daynight_primary"] = False
    base["direct_partition_observation_available"] = False
    base["allocation_validation_basis"] = "indirect_observer_features_only"
    base["LAI_available"] = False
    base["LAI_source"] = "not_available"
    base["harvest_yield_available"] = False
    base["fresh_yield_available"] = False
    base["fresh_yield_source"] = ""
    base["dry_yield_available"] = False
    base["dry_yield_source"] = ""
    base["observed_fruit_FW_g_loadcell"] = np.nan
    base["observed_fruit_DW_g_loadcell_dmc_0p056"] = np.nan
    base["observed_fruit_DW_g_m2_floor_dmc_0p056"] = np.nan
    base["canonical_fruit_DMC_fraction"] = CANONICAL_2025_2C_FRUIT_DMC
    base["fruit_DMC_fraction"] = CANONICAL_2025_2C_FRUIT_DMC
    base["default_fruit_dry_matter_content"] = DEFAULT_FRUIT_DRY_MATTER_CONTENT
    base["DMC_fixed_for_2025_2C"] = True
    base["DMC_sensitivity_enabled"] = False
    base["DMC_sensitivity_values"] = ""
    base["deprecated_previous_default_fruit_DMC_fraction"] = DEPRECATED_PREVIOUS_DEFAULT_FRUIT_DMC
    base["DMC_conversion_performed"] = False
    base["dry_yield_is_dmc_estimated"] = False
    base["direct_dry_yield_measured"] = False
    base["loadcell_floor_area_m2"] = HAF_2025_2C_LOADCELL_FLOOR_AREA_M2
    base["latent_allocation_inference_run"] = False
    base["allocation_promotion_allowed"] = False

    if "apparent_canopy_conductance_available" not in base.columns:
        base["apparent_canopy_conductance_available"] = False
    if "apparent_canopy_conductance" not in base.columns:
        base["apparent_canopy_conductance"] = np.nan
    return base.sort_values([column for column in ("date", "loadcell_id") if column in base.columns]).reset_index(drop=True)
