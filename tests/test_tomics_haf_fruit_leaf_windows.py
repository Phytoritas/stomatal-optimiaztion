import pandas as pd

from stomatal_optimiaztion.domains.tomato.tomics.observers.fruit_diameter_windows import (
    build_fixed_clock_compat_windows,
    build_fruit_leaf_radiation_windows,
)
from stomatal_optimiaztion.domains.tomato.tomics.observers.qc import apply_fruit_leaf_qc
from stomatal_optimiaztion.domains.tomato.tomics.observers.sensor_mapping import load_sensor_mapping


def test_fruit_leaf_windows_are_sensor_level_and_no_p_values() -> None:
    raw = pd.DataFrame(
        {
            "TIMESTAMP": pd.to_datetime(
                [
                    "2025-12-14 06:00",
                    "2025-12-14 18:00",
                    "2025-12-15 06:00",
                ]
            ),
            "Fruit1Diameter_Avg": [30.0, 30.4, 30.7],
            "Fruit2Diameter_Avg": [31.0, 31.2, 31.3],
            "LeafTemp1_Avg": [24.0, 22.0, 23.0],
            "LeafTemp2_Avg": [23.0, 21.0, 22.0],
        }
    )
    qc, _ = apply_fruit_leaf_qc(raw)
    photoperiod = pd.DataFrame(
        {
            "date": ["2025-12-14", "2025-12-15"],
            "threshold_w_m2": [0.0, 0.0],
            "first_light_timestamp": pd.to_datetime(["2025-12-14 06:00", "2025-12-15 06:00"]),
            "last_light_timestamp": pd.to_datetime(["2025-12-14 18:00", "2025-12-15 18:00"]),
        }
    )

    fruit, leaf = build_fruit_leaf_radiation_windows(qc, photoperiod, load_sensor_mapping(), thresholds_w_m2=[0])
    clock = build_fixed_clock_compat_windows(qc, load_sensor_mapping())

    row = fruit[fruit["sensor_column"].eq("Fruit1Diameter_Avg")].iloc[0]
    assert row["radiation_day_net_mm"] == 0.3999999999999986
    assert bool(row["sensor_level_only"]) is True
    assert bool(row["fruit_diameter_p_values_allowed"]) is False
    assert "delta_leaf_temp_lc4_minus_lc1_radiation_day_mean_c" in leaf.columns
    assert clock["fixed_clock_daynight_primary"].eq(False).all()
