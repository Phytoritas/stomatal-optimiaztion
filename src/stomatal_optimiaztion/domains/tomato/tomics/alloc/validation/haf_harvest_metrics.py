from __future__ import annotations

import math

import pandas as pd


METRIC_ID_COLUMNS = [
    "candidate_id",
    "stage",
    "allocator_family",
    "latent_allocation_prior_family",
    "fruit_harvest_family",
    "leaf_harvest_family",
    "observation_operator",
    "fdmc_mode",
]


def _rmse(series: pd.Series) -> float:
    values = pd.to_numeric(series, errors="coerce").dropna()
    if values.empty:
        return math.nan
    return float((values.pow(2).mean()) ** 0.5)


def _mae(series: pd.Series) -> float:
    values = pd.to_numeric(series, errors="coerce").dropna()
    if values.empty:
        return math.nan
    return float(values.abs().mean())


def _r2(measured: pd.Series, model: pd.Series) -> float:
    y_true = pd.to_numeric(measured, errors="coerce")
    y_pred = pd.to_numeric(model, errors="coerce")
    valid = y_true.notna() & y_pred.notna()
    if valid.sum() < 2:
        return math.nan
    truth = y_true[valid]
    residual = truth - y_pred[valid]
    ss_res = float((residual.pow(2)).sum())
    ss_tot = float(((truth - truth.mean()).pow(2)).sum())
    if ss_tot <= 0.0:
        return math.nan
    return float(1.0 - ss_res / ss_tot)


def _first_positive_date(frame: pd.DataFrame, column: str) -> pd.Timestamp | None:
    values = pd.to_numeric(frame[column], errors="coerce").fillna(0.0)
    positive = frame.loc[values.gt(0.0), "date"]
    if positive.empty:
        return None
    return pd.to_datetime(positive.iloc[0])


def _timing_mae_days(frame: pd.DataFrame) -> float:
    measured = _first_positive_date(
        frame,
        "measured_daily_increment_DW_g_m2_floor_dmc_0p056",
    )
    model = _first_positive_date(frame, "model_daily_increment_DW_g_m2_floor")
    if measured is None or model is None:
        return 0.0
    return float(abs((model - measured).days))


def _final_totals(frame: pd.DataFrame) -> tuple[float, float]:
    final_rows = (
        frame.sort_values("date")
        .groupby("loadcell_id", as_index=False)
        .tail(1)
    )
    final_measured = float(
        pd.to_numeric(
            final_rows["measured_cumulative_fruit_DW_g_m2_floor_dmc_0p056"],
            errors="coerce",
        )
        .fillna(0.0)
        .sum()
    )
    final_model = float(
        pd.to_numeric(
            final_rows["model_cumulative_fruit_DW_g_m2_floor"],
            errors="coerce",
        )
        .fillna(0.0)
        .sum()
    )
    return final_measured, final_model


def _metric_row(frame: pd.DataFrame, *, include_loadcell: bool) -> dict[str, object]:
    row = {column: frame[column].iloc[0] for column in METRIC_ID_COLUMNS}
    if include_loadcell:
        row["loadcell_id"] = frame["loadcell_id"].iloc[0]
        row["treatment"] = frame["treatment"].iloc[0]
    final_measured, final_model = _final_totals(frame)
    final_bias = float(final_model - final_measured)
    final_bias_pct = (
        float(final_bias / final_measured * 100.0)
        if pd.notna(final_measured) and abs(float(final_measured)) > 1e-12
        else 0.0
    )
    mass_balance_error = float(
        pd.to_numeric(frame["mass_balance_error"], errors="coerce").fillna(0.0).abs().max()
    )
    leaf_error = float(
        pd.to_numeric(frame["leaf_harvest_mass_balance_error"], errors="coerce")
        .fillna(0.0)
        .abs()
        .max()
    )
    nonfinite = frame[
        [
            "model_cumulative_fruit_DW_g_m2_floor",
            "model_daily_increment_DW_g_m2_floor",
            "measured_cumulative_fruit_DW_g_m2_floor_dmc_0p056",
            "measured_daily_increment_DW_g_m2_floor_dmc_0p056",
        ]
    ].isna().any().any()
    row.update(
        {
            "rmse_cumulative_DW_g_m2_floor": _rmse(
                frame["residual_DW_g_m2_floor"]
            ),
            "mae_cumulative_DW_g_m2_floor": _mae(
                frame["residual_DW_g_m2_floor"]
            ),
            "r2_cumulative_DW_g_m2_floor": _r2(
                frame["measured_cumulative_fruit_DW_g_m2_floor_dmc_0p056"],
                frame["model_cumulative_fruit_DW_g_m2_floor"],
            ),
            "rmse_daily_increment_DW_g_m2_floor": _rmse(
                frame["model_daily_increment_DW_g_m2_floor"]
                - frame["measured_daily_increment_DW_g_m2_floor_dmc_0p056"]
            ),
            "mae_daily_increment_DW_g_m2_floor": _mae(
                frame["model_daily_increment_DW_g_m2_floor"]
                - frame["measured_daily_increment_DW_g_m2_floor_dmc_0p056"]
            ),
            "harvest_timing_mae_days": _timing_mae_days(frame),
            "final_cumulative_bias_DW_g_m2_floor": final_bias,
            "final_cumulative_bias_pct": final_bias_pct,
            "mass_balance_error": mass_balance_error,
            "harvest_mass_balance_error": mass_balance_error,
            "canopy_collapse_days": 0,
            "leaf_harvest_mass_balance_error": leaf_error,
            "budget_units_used": int(frame["budget_units_used"].iloc[0]),
            "budget_parity_group": frame["budget_parity_group"].iloc[0],
            "invalid_run_flag": int(
                bool(frame["invalid_run_flag"].astype(bool).any())
                or mass_balance_error > 1e-6
                or leaf_error > 1e-6
            ),
            "nonfinite_flag": int(bool(nonfinite)),
            "n_dates": int(frame["date"].nunique()),
        }
    )
    return row


def compute_haf_harvest_metrics(
    overlay_df: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    if overlay_df.empty:
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

    by_loadcell_rows = [
        _metric_row(group.sort_values("date"), include_loadcell=True)
        for _, group in overlay_df.groupby([*METRIC_ID_COLUMNS, "loadcell_id", "treatment"])
    ]
    by_loadcell = pd.DataFrame(by_loadcell_rows)

    pooled_rows = [
        _metric_row(group.sort_values(["loadcell_id", "date"]), include_loadcell=False)
        for _, group in overlay_df.groupby(METRIC_ID_COLUMNS)
    ]
    pooled = pd.DataFrame(pooled_rows)

    mean_sd = (
        by_loadcell.groupby([*METRIC_ID_COLUMNS, "treatment"], dropna=False, as_index=False)
        .agg(
            mean_rmse_cumulative_DW_g_m2_floor=(
                "rmse_cumulative_DW_g_m2_floor",
                "mean",
            ),
            sd_rmse_cumulative_DW_g_m2_floor=(
                "rmse_cumulative_DW_g_m2_floor",
                "std",
            ),
            mean_rmse_daily_increment_DW_g_m2_floor=(
                "rmse_daily_increment_DW_g_m2_floor",
                "mean",
            ),
            sd_rmse_daily_increment_DW_g_m2_floor=(
                "rmse_daily_increment_DW_g_m2_floor",
                "std",
            ),
            mean_final_cumulative_bias_pct=("final_cumulative_bias_pct", "mean"),
            sd_final_cumulative_bias_pct=("final_cumulative_bias_pct", "std"),
            n_loadcells=("loadcell_id", "nunique"),
            n_dates=("n_dates", "max"),
        )
        .fillna({"sd_rmse_cumulative_DW_g_m2_floor": 0.0})
        .fillna({"sd_rmse_daily_increment_DW_g_m2_floor": 0.0})
        .fillna({"sd_final_cumulative_bias_pct": 0.0})
    )
    return by_loadcell, pooled, mean_sd


def rank_haf_harvest_candidates(
    pooled_metrics: pd.DataFrame,
    budget_parity: pd.DataFrame,
) -> pd.DataFrame:
    if pooled_metrics.empty:
        return pd.DataFrame()
    budget_cols = [
        "candidate_id",
        "budget_parity_violation",
        "budget_penalty",
    ]
    frame = pooled_metrics.merge(
        budget_parity[budget_cols].drop_duplicates("candidate_id"),
        on="candidate_id",
        how="left",
    )
    frame["budget_parity_violation"] = frame["budget_parity_violation"].fillna(False)
    frame["budget_penalty"] = pd.to_numeric(frame["budget_penalty"], errors="coerce").fillna(0.0)
    frame["ranking_score"] = (
        -1.2 * frame["rmse_cumulative_DW_g_m2_floor"].fillna(1_000.0)
        -0.8 * frame["rmse_daily_increment_DW_g_m2_floor"].fillna(1_000.0)
        -0.3 * frame["final_cumulative_bias_pct"].abs().fillna(1_000.0)
        -100.0 * frame["invalid_run_flag"].fillna(1.0)
        -100.0 * frame["nonfinite_flag"].fillna(1.0)
        -frame["budget_penalty"]
    )
    frame["promotable_in_goal3b"] = False
    return frame.sort_values(
        ["ranking_score", "rmse_cumulative_DW_g_m2_floor"],
        ascending=[False, True],
    ).reset_index(drop=True)


__all__ = [
    "METRIC_ID_COLUMNS",
    "compute_haf_harvest_metrics",
    "rank_haf_harvest_candidates",
]
