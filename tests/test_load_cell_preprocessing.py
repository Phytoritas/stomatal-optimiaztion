from __future__ import annotations

import pandas as pd
import pytest

from stomatal_optimiaztion.domains import load_cell
from stomatal_optimiaztion.domains.load_cell import (
    detect_and_correct_outliers,
    smooth_weight,
)


def test_load_cell_import_surface_exposes_preprocessing_helpers() -> None:
    assert load_cell.detect_and_correct_outliers is detect_and_correct_outliers
    assert load_cell.smooth_weight is smooth_weight


def test_detect_and_correct_outliers_requires_weight_column() -> None:
    with pytest.raises(KeyError, match="weight_kg"):
        detect_and_correct_outliers(pd.DataFrame({"x": [1.0, 2.0]}))


def test_detect_and_correct_outliers_handles_short_series() -> None:
    df = pd.DataFrame({"weight_kg": [1.0, 1.2]})

    out = detect_and_correct_outliers(df)

    assert "dW_raw_kg_s" in out
    assert "is_outlier" in out
    assert out["is_outlier"].tolist() == [False, False]
    assert pd.isna(out.loc[0, "dW_raw_kg_s"])
    assert out.loc[1, "dW_raw_kg_s"] == pytest.approx(0.2)


def test_detect_and_correct_outliers_validates_max_spike_width() -> None:
    df = pd.DataFrame({"weight_kg": [1.0, 1.1, 1.2]})

    with pytest.raises(ValueError, match=">= 1"):
        detect_and_correct_outliers(df, max_spike_width_sec=0)


def test_detect_and_correct_outliers_corrects_impulsive_spike() -> None:
    df = pd.DataFrame(
        {"weight_kg": [1.0, 1.1, 1.0, 1.1, 1.0, 5.0, 1.0, 1.1, 1.0]}
    )

    out = detect_and_correct_outliers(df, k_outlier=1.0, max_spike_width_sec=2)

    assert out["is_outlier"].sum() >= 1
    assert 1.0 <= out.loc[5, "weight_kg"] <= 1.1
    assert out.loc[5, "weight_kg"] < 5.0


def test_smooth_weight_validates_inputs() -> None:
    with pytest.raises(KeyError, match="weight_kg"):
        smooth_weight(pd.DataFrame({"x": [1.0, 2.0, 3.0]}))

    with pytest.raises(ValueError, match=">= 3"):
        smooth_weight(pd.DataFrame({"weight_kg": [1.0, 2.0, 3.0]}), window_sec=2)

    with pytest.raises(ValueError, match="method must be"):
        smooth_weight(
            pd.DataFrame({"weight_kg": [1.0, 2.0, 3.0]}),
            method="median",
            window_sec=3,
        )


def test_smooth_weight_supports_moving_average_and_diff_derivative() -> None:
    df = pd.DataFrame({"weight_kg": [1.0, 2.0, 3.0, 4.0, 5.0]})

    out = smooth_weight(df, method="ma", window_sec=3, derivative_method="diff")

    assert out["weight_smooth_kg"].tolist() == pytest.approx([1.5, 2.0, 3.0, 4.0, 4.5])
    assert pd.isna(out.loc[0, "dW_smooth_kg_s"]) is False
    assert out.loc[1, "dW_smooth_kg_s"] == pytest.approx(0.5)


def test_smooth_weight_supports_savgol_derivative_mode() -> None:
    df = pd.DataFrame({"weight_kg": [0.0, 1.0, 2.0, 3.0, 4.0]})

    out = smooth_weight(
        df,
        method="savgol",
        window_sec=5,
        poly_order=2,
        derivative_method="savgol",
    )

    assert out["weight_smooth_kg"].tolist() == pytest.approx([0, 1, 2, 3, 4], abs=1e-6)
    assert out["dW_smooth_kg_s"].tolist() == pytest.approx([1, 1, 1, 1, 1], abs=1e-6)


def test_smooth_weight_requires_savgol_for_savgol_derivative() -> None:
    df = pd.DataFrame({"weight_kg": [1.0, 2.0, 3.0, 4.0, 5.0]})

    with pytest.raises(ValueError, match="requires method='savgol'"):
        smooth_weight(df, method="ma", window_sec=5, derivative_method="savgol")


def test_smooth_weight_reports_missing_scipy(monkeypatch: pytest.MonkeyPatch) -> None:
    df = pd.DataFrame({"weight_kg": [1.0, 2.0, 3.0, 4.0, 5.0]})
    monkeypatch.setattr(
        "stomatal_optimiaztion.domains.load_cell.preprocessing.savgol_filter",
        None,
    )

    with pytest.raises(RuntimeError, match="scipy"):
        smooth_weight(df, method="savgol", window_sec=5)
