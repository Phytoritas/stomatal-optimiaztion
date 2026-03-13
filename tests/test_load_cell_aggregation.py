from __future__ import annotations

import pandas as pd
import pytest

from stomatal_optimiaztion.domains import load_cell
from stomatal_optimiaztion.domains.load_cell import (
    daily_summary,
    resample_flux_timeseries,
)


def _make_flux_frame() -> pd.DataFrame:
    index = pd.date_range("2025-06-01 00:00:00", periods=4, freq="1s", name="timestamp")
    return pd.DataFrame(
        {
            "irrigation_kg_s": [1.0, 0.0, 0.0, 0.0],
            "drainage_kg_s": [0.0, 1.0, 0.0, 0.0],
            "transpiration_kg_s": [0.1, 0.1, 0.2, 0.2],
            "weight_raw_kg": [10.0, 10.1, 10.2, 10.3],
            "weight_kg": [10.0, 10.1, 10.2, 10.3],
            "water_balance_error_kg": [0.0, 0.1, 0.0, 0.1],
            "is_interpolated": [False, True, False, False],
            "is_outlier": [False, False, True, False],
            "transpiration_scale": [1.0, 1.0, 0.9, 0.9],
            "irrigation_time_sec": [1, 0, 0, 0],
            "drainage_time_sec": [0, 1, 0, 0],
            "substrate_ec_ds": [2.0, 2.2, 2.4, 2.6],
            "substrate_moisture_percent": [30.0, 31.0, 32.0, 33.0],
            "label": ["irrigation", "drainage", "baseline", "baseline"],
        },
        index=index,
    )


def test_load_cell_import_surface_exposes_aggregation_helpers() -> None:
    assert load_cell.resample_flux_timeseries is resample_flux_timeseries
    assert load_cell.daily_summary is daily_summary


def test_resample_flux_timeseries_aggregates_totals_and_rates() -> None:
    out = resample_flux_timeseries(_make_flux_frame(), "2s")

    assert list(out.index.astype(str)) == [
        "2025-06-01 00:00:00",
        "2025-06-01 00:00:02",
    ]
    assert out.loc["2025-06-01 00:00:00", "n_samples"] == 2
    assert out.loc["2025-06-01 00:00:00", "irrigation_kg"] == 1.0
    assert out.loc["2025-06-01 00:00:00", "drainage_kg"] == 1.0
    assert out.loc["2025-06-01 00:00:00", "transpiration_kg"] == 0.2
    assert out.loc["2025-06-01 00:00:00", "irrigation_kg_s"] == 0.5
    assert out.loc["2025-06-01 00:00:00", "drainage_kg_s"] == 0.5
    assert out.loc["2025-06-01 00:00:02", "cum_transpiration_kg"] == pytest.approx(0.6)
    assert out.loc["2025-06-01 00:00:00", "weight_kg_end"] == 10.1
    assert out.loc["2025-06-01 00:00:00", "interpolated_frac"] == 0.5
    assert out.loc["2025-06-01 00:00:02", "outlier_frac"] == 0.5
    assert out.loc["2025-06-01 00:00:00", "irrigation_time_frac"] == 0.5
    assert out.loc["2025-06-01 00:00:00", "substrate_ec_ds"] == 2.1


def test_resample_flux_timeseries_validates_input() -> None:
    frame = _make_flux_frame().reset_index(drop=True)
    with pytest.raises(TypeError, match="DateTimeIndex"):
        resample_flux_timeseries(frame, "2s")

    with pytest.raises(KeyError, match="required flux columns"):
        resample_flux_timeseries(_make_flux_frame()[["weight_kg"]], "2s")

    assert resample_flux_timeseries(_make_flux_frame().iloc[0:0], "2s").empty


def test_daily_summary_uses_events_and_metadata() -> None:
    events_df = pd.DataFrame(
        {
            "start_time": ["2025-06-01 00:00:00", "2025-06-01 12:00:00"],
            "event_type": ["irrigation", "drainage"],
        }
    )

    out = daily_summary(
        _make_flux_frame(),
        events_df=events_df,
        metadata={"irrigation_threshold": 0.3, "drainage_threshold": -0.2},
    )

    assert list(out.index.astype(str)) == ["2025-06-01"]
    assert out.loc["2025-06-01", "n_samples"] == 4
    assert out.loc["2025-06-01", "total_irrigation_kg"] == 1.0
    assert out.loc["2025-06-01", "total_drainage_kg"] == 1.0
    assert out.loc["2025-06-01", "total_transpiration_kg"] == pytest.approx(0.6)
    assert out.loc["2025-06-01", "irrigation_event_count"] == 1
    assert out.loc["2025-06-01", "drainage_event_count"] == 1
    assert out.loc["2025-06-01", "irrigation_time_sec"] == 1
    assert out.loc["2025-06-01", "irrigation_time_frac"] == 0.25
    assert out.loc["2025-06-01", "irrigation_threshold"] == 0.3
    assert out.loc["2025-06-01", "drainage_threshold"] == -0.2


def test_daily_summary_derives_raw_durations_from_labels_when_needed() -> None:
    frame = _make_flux_frame().drop(columns=["irrigation_time_sec", "drainage_time_sec"])

    out = daily_summary(frame)

    assert out.loc["2025-06-01", "irrigation_time_sec_raw"] == 1
    assert out.loc["2025-06-01", "drainage_time_sec_raw"] == 1
    assert out.loc["2025-06-01", "irrigation_time_frac_raw"] == 0.25
    assert out.loc["2025-06-01", "drainage_time_frac_raw"] == 0.25


def test_daily_summary_validates_input() -> None:
    frame = _make_flux_frame().reset_index(drop=True)
    with pytest.raises(TypeError, match="DateTimeIndex"):
        daily_summary(frame)

    assert daily_summary(_make_flux_frame().iloc[0:0]).empty
