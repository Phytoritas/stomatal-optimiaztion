"""Flux decomposition helpers for greenhouse load-cell signals."""

from __future__ import annotations

import pandas as pd


def compute_fluxes_per_second(
    df: pd.DataFrame,
    interpolate_transpiration_during_events: bool = True,
    fix_water_balance: bool = True,
    min_transpiration_scale: float = 0.0,
    max_transpiration_scale: float | None = 3.0,
) -> pd.DataFrame:
    """Split smoothed derivatives into irrigation, drainage, and transpiration."""

    required_cols = {"dW_smooth_kg_s", "label", "weight_smooth_kg"}
    missing = required_cols - set(df.columns)
    if missing:
        raise KeyError(f"Missing required columns for flux computation: {missing}")

    df_out = df.copy()
    d_w = df_out["dW_smooth_kg_s"].fillna(0.0)
    labels = df_out["label"].fillna("baseline")

    irrigation = pd.Series(0.0, index=df_out.index, dtype="float64")
    drainage = pd.Series(0.0, index=df_out.index, dtype="float64")
    transpiration = pd.Series(0.0, index=df_out.index, dtype="float64")

    irrigation_mask = labels == "irrigation"
    drainage_mask = labels == "drainage"
    baseline_mask = labels == "baseline"

    irrigation.loc[irrigation_mask] = d_w.loc[irrigation_mask].clip(lower=0.0)
    drainage.loc[drainage_mask] = (-d_w.loc[drainage_mask]).clip(lower=0.0)
    transp_mask = baseline_mask & (d_w <= 0)
    transpiration.loc[transp_mask] = -d_w.loc[transp_mask]

    if interpolate_transpiration_during_events and transpiration.gt(0).sum() >= 2:
        interp_series = transpiration.copy()
        event_segments = (labels != "baseline") & (interp_series <= 0)
        interp_series = interp_series.mask(event_segments, float("nan"))
        interp_series = interp_series.interpolate(limit_area="inside")
        transpiration = interp_series.fillna(transpiration)

    df_out["irrigation_kg_s"] = irrigation
    df_out["drainage_kg_s"] = drainage
    df_out["transpiration_kg_s"] = transpiration

    df_out["cum_irrigation_kg"] = irrigation.cumsum()
    df_out["cum_drainage_kg"] = drainage.cumsum()
    df_out["cum_transpiration_kg"] = transpiration.cumsum()

    weight_series = df_out["weight_smooth_kg"].ffill()
    initial_weight = weight_series.iloc[0]
    reconstructed = (
        initial_weight
        + df_out["cum_irrigation_kg"]
        - df_out["cum_drainage_kg"]
        - df_out["cum_transpiration_kg"]
    )
    balance_error = weight_series - reconstructed
    df_out["water_balance_error_before_fix_kg"] = balance_error

    scale_applied = 1.0
    if fix_water_balance and not balance_error.empty:
        final_bias = balance_error.iloc[-1]
        if abs(final_bias) > 1e-6:
            transp_total = transpiration.sum()
            if transp_total > 0:
                scale = float(1 - final_bias / transp_total)
                if not pd.notna(scale):
                    scale = 1.0
                if max_transpiration_scale is not None:
                    scale = min(scale, float(max_transpiration_scale))
                scale = max(scale, float(min_transpiration_scale))
                scale_applied = scale
                transpiration = (transpiration * scale).clip(lower=0.0)
                df_out["transpiration_kg_s"] = transpiration
                df_out["cum_transpiration_kg"] = transpiration.cumsum()
                reconstructed = (
                    initial_weight
                    + df_out["cum_irrigation_kg"]
                    - df_out["cum_drainage_kg"]
                    - df_out["cum_transpiration_kg"]
                )
                balance_error = weight_series - reconstructed

    df_out["transpiration_scale"] = float(scale_applied)
    df_out["reconstructed_weight_kg"] = reconstructed
    df_out["water_balance_error_kg"] = balance_error

    return df_out
