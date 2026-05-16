from __future__ import annotations

import numpy as np
import pandas as pd


def _clip01(value: pd.Series) -> pd.Series:
    return value.clip(lower=0.0, upper=1.0)


def build_rootzone_indices(
    dataset2_frame: pd.DataFrame,
    daily_et: pd.DataFrame | None = None,
    *,
    eps: float = 1e-9,
) -> pd.DataFrame:
    frame = dataset2_frame.copy()
    if "date" not in frame.columns and "timestamp" in frame.columns:
        frame["date"] = pd.to_datetime(frame["timestamp"], errors="coerce").dt.strftime("%Y-%m-%d")
    if "date" in frame.columns:
        frame["date"] = frame["date"].astype(str)
    group_cols = [column for column in ("date", "loadcell_id", "treatment") if column in frame.columns]
    if not group_cols:
        return pd.DataFrame()

    if {"moisture_percent_mean", "ec_ds_mean", "tensiometer_hp_mean"}.intersection(frame.columns):
        agg = frame.copy()
        if "source_row_count" in agg.columns:
            agg["row_count"] = pd.to_numeric(agg["source_row_count"], errors="coerce")
        elif "row_count" not in agg.columns:
            agg["row_count"] = 1
        if "tensiometer_hp_count" in agg.columns:
            agg["tensiometer_count"] = pd.to_numeric(agg["tensiometer_hp_count"], errors="coerce")
        elif "tensiometer_count" not in agg.columns:
            agg["tensiometer_count"] = agg["tensiometer_hp_mean"].notna().astype("int64")
        for column in ("moisture_percent_mean", "ec_ds_mean", "tensiometer_hp_mean"):
            if column not in agg.columns:
                agg[column] = np.nan
    else:
        agg = (
            frame.groupby(group_cols, dropna=False)
            .agg(
                moisture_percent_mean=("moisture_percent", "mean") if "moisture_percent" in frame.columns else ("date", "size"),
                ec_ds_mean=("ec_ds", "mean") if "ec_ds" in frame.columns else ("date", "size"),
                tensiometer_hp_mean=("tensiometer_hp", "mean") if "tensiometer_hp" in frame.columns else ("date", "size"),
                tensiometer_count=("tensiometer_hp", "count") if "tensiometer_hp" in frame.columns else ("date", "size"),
                row_count=("date", "size") if "date" in frame.columns else (group_cols[0], "size"),
            )
            .reset_index()
        )
        if "moisture_percent" not in frame.columns:
            agg["moisture_percent_mean"] = np.nan
        if "ec_ds" not in frame.columns:
            agg["ec_ds_mean"] = np.nan
        if "tensiometer_hp" not in frame.columns:
            agg["tensiometer_hp_mean"] = np.nan
            agg["tensiometer_count"] = 0

    agg["tensiometer_available"] = agg["tensiometer_count"].gt(0)
    agg["tensiometer_coverage_fraction"] = agg["tensiometer_count"] / agg["row_count"].replace(0, np.nan)

    date_col = "date"
    control = (
        agg[agg.get("treatment", "").eq("Control")].groupby(date_col)["moisture_percent_mean"].mean().rename("theta_control_group")
        if "treatment" in agg.columns
        else pd.Series(dtype=float)
    )
    drought = (
        agg[agg.get("treatment", "").eq("Drought")].groupby(date_col)["moisture_percent_mean"].mean().rename("theta_drought_group")
        if "treatment" in agg.columns
        else pd.Series(dtype=float)
    )
    group_theta = pd.concat([control, drought], axis=1).reset_index()
    agg = agg.merge(group_theta, on=date_col, how="left")
    agg["RZI_theta_group"] = _clip01(1.0 - agg["theta_drought_group"] / (agg["theta_control_group"] + eps))

    paired = agg.pivot_table(index=date_col, columns="loadcell_id", values="moisture_percent_mean", aggfunc="mean")
    if 1 in paired.columns and 4 in paired.columns:
        paired_rzi = _clip01(1.0 - paired[4] / (paired[1] + eps)).rename("RZI_theta_paired").reset_index()
        agg = agg.merge(paired_rzi, on=date_col, how="left")
    else:
        agg["RZI_theta_paired"] = np.nan

    agg["RZI_AW_t"] = np.where(
        agg.get("treatment", "").eq("Drought") if "treatment" in agg.columns else False,
        _clip01(1.0 - agg["moisture_percent_mean"] / (agg["theta_control_group"] + eps)),
        0.0,
    )
    agg.loc[agg["theta_control_group"].isna(), "RZI_AW_t"] = np.nan

    agg["RZI_main"] = agg["RZI_theta_paired"]
    agg["RZI_main_source"] = np.where(agg["RZI_main"].notna(), "theta_paired_lc4_vs_lc1", "unavailable")
    missing = agg["RZI_main"].isna() & agg["RZI_theta_group"].notna()
    agg.loc[missing, "RZI_main"] = agg.loc[missing, "RZI_theta_group"]
    agg.loc[missing, "RZI_main_source"] = "theta_group_drought_vs_control"
    missing = agg["RZI_main"].isna() & agg["RZI_AW_t"].notna()
    agg.loc[missing, "RZI_main"] = agg.loc[missing, "RZI_AW_t"]
    agg.loc[missing, "RZI_main_source"] = "AW_vs_control"

    if daily_et is not None and not daily_et.empty:
        et = daily_et.copy()
        et["radiation_total_ET_g"] = et.get("radiation_total_ET_g", et.get("radiation_day_ET_g", 0) + et.get("radiation_night_ET_g", 0))
        if "env_vpd_kpa_mean" not in et.columns and "day_vpd_kpa_mean" in et.columns:
            et["env_vpd_kpa_mean"] = et["day_vpd_kpa_mean"]
        if "env_vpd_kpa_mean" not in et.columns:
            et["env_vpd_kpa_mean"] = np.nan
        merge_cols = [column for column in ("date", "loadcell_id", "treatment") if column in agg.columns and column in et.columns]
        agg = agg.merge(et[merge_cols + ["radiation_total_ET_g", "env_vpd_kpa_mean"]], on=merge_cols, how="left")
        agg["apparent_canopy_conductance"] = agg["radiation_total_ET_g"] / (agg["env_vpd_kpa_mean"] + eps)
        agg["apparent_canopy_conductance_available"] = agg["apparent_canopy_conductance"].notna()
    else:
        agg["apparent_canopy_conductance"] = np.nan
        agg["apparent_canopy_conductance_available"] = False

    for loadcell_id in (4, 5):
        values = agg[agg["loadcell_id"].eq(loadcell_id)][[date_col, "tensiometer_hp_mean"]].rename(
            columns={"tensiometer_hp_mean": f"lc{loadcell_id}_tensiometer_hp_mean"}
        )
        agg = agg.merge(values, on=date_col, how="left")
    drought_tension = (
        agg[agg.get("treatment", "").eq("Drought")].groupby(date_col)["tensiometer_hp_mean"].mean().rename("drought_group_tensiometer_hp_mean")
        if "treatment" in agg.columns
        else pd.Series(dtype=float)
    )
    agg = agg.merge(drought_tension.reset_index(), on=date_col, how="left")
    agg["rootzone_bridge_status"] = np.where(agg["tensiometer_available"], "matched_date_loadcell", "matched_date_loadcell_no_tensiometer")
    agg["warnings"] = np.where(agg["theta_control_group"].isna(), "control_reference_unavailable", "")
    return agg[
        [
            *group_cols,
            "moisture_percent_mean",
            "ec_ds_mean",
            "tensiometer_hp_mean",
            "lc4_tensiometer_hp_mean",
            "lc5_tensiometer_hp_mean",
            "drought_group_tensiometer_hp_mean",
            "tensiometer_available",
            "tensiometer_coverage_fraction",
            "RZI_AW_t",
            "RZI_theta_paired",
            "RZI_theta_group",
            "RZI_main",
            "RZI_main_source",
            "apparent_canopy_conductance",
            "apparent_canopy_conductance_available",
            "rootzone_bridge_status",
            "warnings",
        ]
    ].sort_values(group_cols).reset_index(drop=True)
