import pandas as pd

from stomatal_optimiaztion.domains.tomato.tomics.observers.radiation_windows import (
    add_clock_compatibility_audit,
    build_photoperiod_table,
    build_radiation_intervals,
)


def test_radiation_thresholds_define_day_not_clock() -> None:
    frame = pd.DataFrame(
        {
            "timestamp": pd.to_datetime(
                [
                    "2025-12-14 05:59:00",
                    "2025-12-14 06:01:00",
                    "2025-12-14 06:11:00",
                    "2025-12-14 18:01:00",
                ]
            ),
            "loadcell_id": [1, 1, 1, 1],
            "treatment": ["Control"] * 4,
            "env_inside_radiation_wm2": [0.0, 0.5, 6.0, 0.0],
        }
    )

    intervals = build_radiation_intervals(frame)
    main = intervals[intervals["threshold_w_m2"].eq(0.0)]
    threshold_5 = intervals[intervals["threshold_w_m2"].eq(5.0)]
    photoperiod = build_photoperiod_table(intervals)
    clock = add_clock_compatibility_audit(frame.rename(columns={"timestamp": "TIMESTAMP"}))

    assert main[main["interval_start"].eq(pd.Timestamp("2025-12-14 06:00"))]["radiation_phase"].iloc[0] == "day"
    assert threshold_5[threshold_5["interval_start"].eq(pd.Timestamp("2025-12-14 06:00"))]["radiation_phase"].iloc[0] == "night"
    assert photoperiod["radiation_column_used"].eq("env_inside_radiation_wm2").all()
    assert clock["fixed_clock_daynight_primary"].eq(False).all()

