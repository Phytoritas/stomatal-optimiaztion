from __future__ import annotations

from unittest.mock import Mock

import pandas as pd
import pytest

from stomatal_optimiaztion.domains import load_cell
from stomatal_optimiaztion.domains.load_cell import auto_detect_step_thresholds


def test_load_cell_import_surface_exposes_threshold_helper() -> None:
    assert load_cell.auto_detect_step_thresholds is auto_detect_step_thresholds


def test_auto_detect_step_thresholds_rejects_none_and_empty_series() -> None:
    with pytest.raises(ValueError, match="cannot be None"):
        auto_detect_step_thresholds(None)  # type: ignore[arg-type]

    with pytest.raises(ValueError, match="empty derivative series"):
        auto_detect_step_thresholds(pd.Series([], dtype=float))


def test_auto_detect_step_thresholds_falls_back_when_valid_mask_removes_all() -> None:
    d_w_smooth = pd.Series([0.0, 0.01, -0.01, 0.02, -0.02])
    valid_mask = pd.Series([False, False, False, False, False])

    unmasked = auto_detect_step_thresholds(d_w_smooth)
    masked = auto_detect_step_thresholds(d_w_smooth, valid_mask=valid_mask)

    assert masked == unmasked


def test_auto_detect_step_thresholds_uses_minimum_sigma_fallback() -> None:
    irrigation_threshold, drainage_threshold = auto_detect_step_thresholds(
        pd.Series([0.0, 0.0, 0.0, 0.0])
    )

    assert irrigation_threshold == pytest.approx(4e-6)
    assert drainage_threshold == pytest.approx(-4e-6)


def test_auto_detect_step_thresholds_enforces_sign_constraints_and_logs() -> None:
    d_w_smooth = pd.Series(
        [-0.3, -0.2, -0.01, 0.0, 0.01, 0.2, 0.3],
        index=pd.RangeIndex(7),
    )
    logger = Mock()

    irrigation_threshold, drainage_threshold = auto_detect_step_thresholds(
        d_w_smooth,
        logger=logger,
    )

    assert irrigation_threshold >= 0.0
    assert drainage_threshold <= 0.0
    assert irrigation_threshold > drainage_threshold
    logger.info.assert_called_once()
