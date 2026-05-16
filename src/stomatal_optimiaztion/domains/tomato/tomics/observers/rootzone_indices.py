from __future__ import annotations

import numpy as np
import pandas as pd


def _clip01(value: pd.Series) -> pd.Series:
    return value.clip(lower=0.0, upper=1.0)


def build_rootzone_indices(
    dataset2_frame: pd.DataFrame,
    daily_et: pd.DataFrame | None = None,
    *,
    dataset1_reference_frame: pd.DataFrame | None = None,
    eps: float = 1e-9,
) -> pd.DataFrame:
    frame = dataset2_frame.copy()
    if "date" not in frame.columns and "timestamp" in frame.columns:
        frame["date"] = pd.to_datetime(frame["timestamp"], errors="coerce").dt.strftime("%Y-%m-%d")
    if "date" in frame.columns:
        frame["date"] = frame["date"].astype(str)
    dataset2_group_cols = [column for column in ("date", "loadcell_id", "treatment") if column in frame.columns]
    if not dataset2_group_cols and (dataset1_reference_frame is None or dataset1_reference_frame.empty):
        return pd.DataFrame()

    if {"moisture_percent_mean", "ec_ds_mean", "tensiometer_hp_mean"}.intersection(frame.columns):
        dataset2_agg = frame.copy()
        if "source_row_count" in dataset2_agg.columns:
            dataset2_agg["row_count"] = pd.to_numeric(dataset2_agg["source_row_count"], errors="coerce")
        elif "row_count" not in dataset2_agg.columns:
            dataset2_agg["row_count"] = 1
        if "tensiometer_hp_count" in dataset2_agg.columns:
            dataset2_agg["tensiometer_count"] = pd.to_numeric(dataset2_agg["tensiometer_hp_count"], errors="coerce")
        elif "tensiometer_count" not in dataset2_agg.columns:
            dataset2_agg["tensiometer_count"] = dataset2_agg["tensiometer_hp_mean"].notna().astype("int64")
        for column in ("moisture_percent_mean", "ec_ds_mean", "tensiometer_hp_mean"):
            if column not in dataset2_agg.columns:
                dataset2_agg[column] = np.nan
    else:
        dataset2_agg = (
            frame.groupby(dataset2_group_cols, dropna=False)
            .agg(
                moisture_percent_mean=("moisture_percent", "mean") if "moisture_percent" in frame.columns else ("date", "size"),
                ec_ds_mean=("ec_ds", "mean") if "ec_ds" in frame.columns else ("date", "size"),
                tensiometer_hp_mean=("tensiometer_hp", "mean") if "tensiometer_hp" in frame.columns else ("date", "size"),
                tensiometer_count=("tensiometer_hp", "count") if "tensiometer_hp" in frame.columns else ("date", "size"),
                row_count=("date", "size") if "date" in frame.columns else (dataset2_group_cols[0], "size"),
            )
            .reset_index()
        )
        if "moisture_percent" not in frame.columns:
            dataset2_agg["moisture_percent_mean"] = np.nan
        if "ec_ds" not in frame.columns:
            dataset2_agg["ec_ds_mean"] = np.nan
        if "tensiometer_hp" not in frame.columns:
            dataset2_agg["tensiometer_hp_mean"] = np.nan
            dataset2_agg["tensiometer_count"] = 0

    dataset2_agg["tensiometer_available"] = dataset2_agg["tensiometer_count"].gt(0)
    dataset2_agg["tensiometer_coverage_fraction"] = dataset2_agg["tensiometer_count"] / dataset2_agg["row_count"].replace(0, np.nan)

    reference_source = "dataset2_moisture"
    if dataset1_reference_frame is not None and not dataset1_reference_frame.empty:
        ref = dataset1_reference_frame.copy()
        if "date" not in ref.columns and "timestamp" in ref.columns:
            ref["date"] = pd.to_datetime(ref["timestamp"], errors="coerce").dt.strftime("%Y-%m-%d")
        if "date" in ref.columns:
            ref["date"] = ref["date"].astype(str)
        ref_group_cols = [column for column in ("date", "loadcell_id", "treatment") if column in ref.columns]
        if {"moisture_percent_mean", "ec_ds_mean"}.intersection(ref.columns):
            agg = ref.copy()
            if "source_row_count" in agg.columns:
                agg["row_count"] = pd.to_numeric(agg["source_row_count"], errors="coerce")
            elif "row_count" not in agg.columns:
                agg["row_count"] = 1
            for column in ("moisture_percent_mean", "ec_ds_mean"):
                if column not in agg.columns:
                    agg[column] = np.nan
        else:
            candidate_agg = (
                ref.groupby(ref_group_cols, dropna=False)
                .agg(
                    moisture_percent_mean=("moisture_percent", "mean") if "moisture_percent" in ref.columns else ("date", "size"),
                    ec_ds_mean=("ec_ds", "mean") if "ec_ds" in ref.columns else ("date", "size"),
                    row_count=("date", "size") if "date" in ref.columns else (ref_group_cols[0], "size"),
                )
                .reset_index()
            )
            if "moisture_percent" not in ref.columns:
                candidate_agg["moisture_percent_mean"] = np.nan
            if "ec_ds" not in ref.columns:
                candidate_agg["ec_ds_mean"] = np.nan
            agg = candidate_agg
        if "moisture_percent_mean" in agg.columns and agg["moisture_percent_mean"].notna().any():
            reference_source = "dataset1_moisture_lc1_lc6"
        else:
            agg = dataset2_agg.copy()
            reference_source = "dataset2_moisture"
    else:
        agg = dataset2_agg.copy()

    group_cols = [column for column in ("date", "loadcell_id", "treatment") if column in agg.columns]
    if not group_cols:
        return pd.DataFrame()
    agg["tensiometer_hp_mean"] = np.nan
    agg["tensiometer_available"] = False
    agg["tensiometer_coverage_fraction"] = 0.0
    agg["tensiometer_count"] = 0
    if not dataset2_agg.empty:
        tension_cols = [
            column
            for column in (
                "date",
                "loadcell_id",
                "treatment",
                "tensiometer_hp_mean",
                "tensiometer_available",
                "tensiometer_coverage_fraction",
                "tensiometer_count",
            )
            if column in dataset2_agg.columns
        ]
        agg = agg.drop(
            columns=[
                column
                for column in (
                    "tensiometer_hp_mean",
                    "tensiometer_available",
                    "tensiometer_coverage_fraction",
                    "tensiometer_count",
                )
                if column in agg.columns
            ],
            errors="ignore",
        )
        agg = agg.merge(dataset2_agg[tension_cols], on=[column for column in ("date", "loadcell_id", "treatment") if column in tension_cols and column in agg.columns], how="left")
        agg["tensiometer_hp_mean"] = agg.get("tensiometer_hp_mean", np.nan)
        agg["tensiometer_available"] = agg.get("tensiometer_available", False).fillna(False)
        agg["tensiometer_coverage_fraction"] = agg.get("tensiometer_coverage_fraction", 0.0).fillna(0.0)
        agg["tensiometer_count"] = agg.get("tensiometer_count", 0).fillna(0)

    dataset2_has_control = bool(
        "treatment" in dataset2_agg.columns and dataset2_agg["treatment"].astype(str).eq("Control").any()
    )
    dataset2_has_tensiometer = bool(dataset2_agg.get("tensiometer_available", pd.Series(dtype=bool)).fillna(False).any())
    agg["Dataset2_tensiometer_drought_only"] = bool(dataset2_has_tensiometer and not dataset2_has_control)
    agg["tensiometer_extrapolated_to_all_loadcells"] = False
    agg["RZI_control_reference_source"] = reference_source

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
    agg["RZI_main_available"] = agg["RZI_main"].notna()

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
            "RZI_main_available",
            "RZI_control_reference_source",
            "Dataset2_tensiometer_drought_only",
            "tensiometer_extrapolated_to_all_loadcells",
            "apparent_canopy_conductance",
            "apparent_canopy_conductance_available",
            "rootzone_bridge_status",
            "warnings",
        ]
    ].sort_values(group_cols).reset_index(drop=True)
