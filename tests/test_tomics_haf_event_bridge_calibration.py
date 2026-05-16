import pandas as pd

from stomatal_optimiaztion.domains.tomato.tomics.observers.water_flux_event_bridge import (
    build_10min_event_bridged_water_loss,
    calibrate_to_daily_event_bridged_total,
)


def test_event_bridge_rate_mapping_and_daily_calibration() -> None:
    intervals = build_10min_event_bridged_water_loss(
        pd.DataFrame(
            {
                "interval_start": pd.date_range("2025-12-14", periods=2, freq="10min"),
                "date": ["2025-12-14", "2025-12-14"],
                "loadcell_id": [1, 1],
                "treatment": ["Control", "Control"],
                "quiet_loss_rate_g_h": [60.0, 60.0],
                "bridge_loss_rate_g_h": [60.0, 120.0],
                "event_flag": [False, True],
            }
        )
    )
    calibrated = calibrate_to_daily_event_bridged_total(
        intervals,
        pd.DataFrame(
            {
                "date": ["2025-12-14"],
                "loadcell_id": [1],
                "treatment": ["Control"],
                "existing_daily_event_bridged_loss_g_per_day": [60.0],
            }
        ),
    )

    assert intervals["loss_g_10min_unscaled"].tolist() == [10.0, 20.0]
    assert calibrated["daily_bridge_scale_factor"].iloc[0] == 2.0
    assert calibrated["loss_g_10min_event_bridged_calibrated"].tolist() == [20.0, 40.0]


def test_event_bridge_missing_daily_total_is_safe_uncalibrated() -> None:
    intervals = build_10min_event_bridged_water_loss(
        pd.DataFrame(
            {
                "interval_start": pd.date_range("2025-12-14", periods=1, freq="10min"),
                "date": ["2025-12-14"],
                "loadcell_id": [1],
                "treatment": ["Control"],
                "quiet_loss_rate_g_h": [60.0],
                "event_flag": [False],
            }
        )
    )
    calibrated = calibrate_to_daily_event_bridged_total(intervals)

    assert calibrated["bridge_status"].iloc[0] == "uncalibrated_no_daily_total"
    assert calibrated["loss_g_10min_event_bridged_calibrated"].isna().all()

