"""Preprocessing utilities for load-cell weight signals."""

from __future__ import annotations

import numpy as np
import pandas as pd

try:
    from scipy.signal import savgol_filter
except ImportError:  # pragma: no cover - optional dependency
    savgol_filter = None


def detect_and_correct_outliers(
    df: pd.DataFrame,
    k_outlier: float = 10.0,
    max_spike_width_sec: int = 2,
) -> pd.DataFrame:
    """Identify derivative spikes and correct suspicious weight samples."""

    if "weight_kg" not in df:
        raise KeyError("Input DataFrame must contain 'weight_kg'.")

    if len(df) < 3:
        df_copy = df.copy()
        df_copy["dW_raw_kg_s"] = df_copy["weight_kg"].diff()
        df_copy["is_outlier"] = False
        return df_copy

    if max_spike_width_sec < 1:
        raise ValueError("max_spike_width_sec must be >= 1.")

    df_out = df.copy()
    weight = df_out["weight_kg"].astype(float)
    d_w_raw = weight.diff()
    df_out["dW_raw_kg_s"] = d_w_raw

    d_w_non_na = d_w_raw.dropna()
    if d_w_non_na.empty:
        df_out["is_outlier"] = False
        return df_out

    q_low, q_high = d_w_non_na.quantile([0.1, 0.9])
    central = d_w_non_na[(d_w_non_na >= q_low) & (d_w_non_na <= q_high)]
    if central.empty:
        central = d_w_non_na

    median = central.median(skipna=True)
    mad = (central - median).abs().median(skipna=True)
    noise_sigma = float(1.4826 * mad) if pd.notna(mad) else 0.0

    threshold = k_outlier * noise_sigma
    if threshold <= 0 or np.isnan(threshold):
        df_out["is_outlier"] = False
        return df_out

    candidate = d_w_raw.abs() > threshold
    candidate = candidate.fillna(False)

    run_id = (candidate != candidate.shift(1)).cumsum()
    run_lengths = candidate.groupby(run_id).transform("sum")
    short_run = candidate & (run_lengths <= max_spike_width_sec)

    opposite_next = (d_w_raw * d_w_raw.shift(-1) < 0) & (
        d_w_raw.shift(-1).abs() > threshold
    )
    opposite_prev = (d_w_raw * d_w_raw.shift(1) < 0) & (
        d_w_raw.shift(1).abs() > threshold
    )
    impulsive = opposite_next.fillna(False) | opposite_prev.fillna(False)

    outlier_mask = short_run & (impulsive | (max_spike_width_sec > 1))
    outlier_mask = outlier_mask.fillna(False)
    df_out["is_outlier"] = outlier_mask

    if outlier_mask.any():
        corrected = weight.copy()
        corrected.loc[outlier_mask] = np.nan
        corrected = corrected.interpolate(
            method="linear",
            limit_direction="both",
        )
        df_out["weight_kg"] = corrected

    return df_out


def smooth_weight(
    df: pd.DataFrame,
    method: str = "savgol",
    window_sec: int = 31,
    poly_order: int = 2,
    derivative_method: str = "central",
) -> pd.DataFrame:
    """Smooth weight and compute per-second derivatives."""

    if "weight_kg" not in df:
        raise KeyError("Input DataFrame must contain 'weight_kg'.")

    if window_sec < 3:
        raise ValueError("window_sec must be >= 3 seconds.")

    df_out = df.copy()
    weight = df_out["weight_kg"].astype(float)
    method = method.lower()
    derivative_method = derivative_method.lower()

    if method in {"ma", "moving_average"}:
        smoothed = weight.rolling(window=window_sec, center=True, min_periods=1).mean()
    elif method == "savgol":
        if savgol_filter is None:
            raise RuntimeError(
                "scipy is required for Savitzky-Golay smoothing but is not installed.",
            )
        series_len = len(weight)
        if series_len < poly_order + 2:
            raise ValueError(
                "Time series is too short for requested Savitzky-Golay parameters.",
            )
        window_length = window_sec
        if window_length % 2 == 0:
            window_length += 1
        min_window = poly_order + 2
        if min_window % 2 == 0:
            min_window += 1
        window_length = max(window_length, min_window)
        max_window = series_len if series_len % 2 == 1 else series_len - 1
        window_length = min(window_length, max_window)
        smoothed = pd.Series(
            savgol_filter(
                weight.to_numpy(),
                window_length=window_length,
                polyorder=min(poly_order, window_length - 1),
                mode="interp",
            ),
            index=weight.index,
        )
    else:
        raise ValueError("method must be 'ma' or 'savgol'.")

    df_out["weight_smooth_kg"] = smoothed

    if derivative_method == "diff":
        d_w = smoothed.diff()
    elif derivative_method == "central":
        if len(smoothed) < 2:
            d_w = smoothed.copy() * 0.0
        else:
            d_w = (smoothed.shift(-1) - smoothed.shift(1)) / 2.0
            d_w.iloc[0] = smoothed.iloc[1] - smoothed.iloc[0]
            d_w.iloc[-1] = smoothed.iloc[-1] - smoothed.iloc[-2]
    elif derivative_method == "savgol":
        if method != "savgol":
            raise ValueError("derivative_method='savgol' requires method='savgol'.")
        if savgol_filter is None:
            raise RuntimeError(
                "scipy is required for Savitzky-Golay derivative but is not installed.",
            )
        series_len = len(weight)
        window_length = window_sec
        if window_length % 2 == 0:
            window_length += 1
        min_window = poly_order + 2
        if min_window % 2 == 0:
            min_window += 1
        window_length = max(window_length, min_window)
        max_window = series_len if series_len % 2 == 1 else series_len - 1
        window_length = min(window_length, max_window)
        d_w = pd.Series(
            savgol_filter(
                weight.to_numpy(),
                window_length=window_length,
                polyorder=min(poly_order, window_length - 1),
                deriv=1,
                delta=1.0,
                mode="interp",
            ),
            index=weight.index,
        )
    else:
        raise ValueError("derivative_method must be 'diff', 'central', or 'savgol'.")

    df_out["dW_smooth_kg_s"] = pd.Series(d_w, index=smoothed.index).fillna(0.0)

    return df_out
