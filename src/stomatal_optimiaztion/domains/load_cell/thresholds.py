"""Automatic threshold detection for irrigation and drainage events."""

from __future__ import annotations

import logging

import numpy as np
import pandas as pd


def auto_detect_step_thresholds(
    d_w_smooth: pd.Series,
    min_pos_events: int = 5,
    min_neg_events: int = 5,
    k_tail: float = 4.0,
    min_factor: float = 3.0,
    valid_mask: pd.Series | None = None,
    logger: logging.Logger | None = None,
) -> tuple[float, float]:
    """Estimate irrigation and drainage thresholds from a derivative series."""

    if d_w_smooth is None:
        raise ValueError("dW_smooth cannot be None.")

    x = pd.Series(d_w_smooth)
    if valid_mask is not None:
        vm = pd.Series(valid_mask, index=x.index).fillna(False).astype(bool)
        filtered = x[vm]
        x = filtered if filtered.dropna().size > 0 else x
    x = x.dropna()
    if x.empty:
        raise ValueError("Cannot detect thresholds from empty derivative series.")

    p_low, p_high = x.quantile([0.05, 0.95])
    central = x[(x >= p_low) & (x <= p_high)]
    if central.empty:
        central = x

    m0 = central.median()
    mad = (central - m0).abs().median()
    if pd.notna(mad) and mad > 0:
        noise_sigma = float(1.4826 * mad)
    else:
        noise_sigma = 0.0
    if noise_sigma <= 0:
        candidates = [
            float(central.std(ddof=0)),
            float((central - m0).abs().median()),
            1e-6,
        ]
        finite_candidates = [c for c in candidates if np.isfinite(c) and c > 0]
        noise_sigma = max(finite_candidates) if finite_candidates else 1e-6

    irrigation_threshold = float(m0 + k_tail * noise_sigma)
    drainage_threshold = float(m0 - k_tail * noise_sigma)

    irrigation_threshold = max(
        irrigation_threshold, float(m0 + min_factor * noise_sigma)
    )
    drainage_threshold = min(
        drainage_threshold, float(m0 - min_factor * noise_sigma)
    )

    irrigation_threshold = max(irrigation_threshold, 0.0)
    drainage_threshold = min(drainage_threshold, 0.0)

    high_pos = x[x >= irrigation_threshold]
    high_neg = x[x <= drainage_threshold]
    if logger:
        logger.info(
            "Auto thresholds -> m0=%.4g, sigma=%.4g, pos_tail=%d, neg_tail=%d, irrig=%.4g, drain=%.4g",
            float(m0),
            noise_sigma,
            len(high_pos),
            len(high_neg),
            irrigation_threshold,
            drainage_threshold,
        )

    return float(irrigation_threshold), float(drainage_threshold)
