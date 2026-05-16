import pandas as pd

from stomatal_optimiaztion.domains.tomato.tomics.observers.qc import apply_fruit_leaf_qc


def test_fruit_diameter_qc_range_and_jump_rules() -> None:
    frame = pd.DataFrame(
        {
            "TIMESTAMP": pd.date_range("2025-12-14 06:00", periods=5, freq="10min"),
            "Fruit1Diameter_Avg": [30.0, 30.3, 121.0, 31.0, 33.0],
            "LeafTemp1_Avg": [22.0, 22.1, 22.2, 22.3, 22.4],
        }
    )

    qc, report = apply_fruit_leaf_qc(
        frame,
        fruit_columns=["Fruit1Diameter_Avg"],
        leaf_columns=["LeafTemp1_Avg"],
    )

    assert qc.loc[2, "Fruit1Diameter_Avg_qc_reason"] == "outside_20_120_mm"
    assert qc.loc[4, "Fruit1Diameter_Avg_qc_reason"] == "jump_gt_1_mm"
    fruit_report = report[report["sensor_column"].eq("Fruit1Diameter_Avg")].iloc[0]
    assert bool(fruit_report["insufficient_valid_points"]) is True
