import pandas as pd

from stomatal_optimiaztion.domains.tomato.tomics.observers.rootzone_indices import build_rootzone_indices


def test_dataset1_moisture_reference_drives_rzi_while_dataset2_tensiometer_is_drought_only() -> None:
    dataset1_reference = pd.DataFrame(
        {
            "date": ["2025-12-14", "2025-12-14", "2025-12-14", "2025-12-14"],
            "loadcell_id": [1, 2, 4, 5],
            "treatment": ["Control", "Control", "Drought", "Drought"],
            "moisture_percent": [80.0, 82.0, 40.0, 42.0],
            "ec_ds": [2.0, 2.1, 2.8, 2.9],
        }
    )
    dataset2 = pd.DataFrame(
        {
            "date": ["2025-12-14", "2025-12-14"],
            "loadcell_id": [4, 5],
            "treatment": ["Drought", "Drought"],
            "moisture_percent": [39.0, 41.0],
            "ec_ds": [2.7, 2.8],
            "tensiometer_hp": [-20.0, -22.0],
        }
    )

    rootzone = build_rootzone_indices(dataset2, dataset1_reference_frame=dataset1_reference)
    drought_lc4 = rootzone[rootzone["loadcell_id"].eq(4)].iloc[0]

    assert bool(drought_lc4["RZI_main_available"]) is True
    assert drought_lc4["RZI_main_source"] == "theta_paired_lc4_vs_lc1"
    assert drought_lc4["RZI_main"] > 0
    assert drought_lc4["RZI_control_reference_source"] == "dataset1_moisture_lc1_lc6"
    assert bool(drought_lc4["Dataset2_tensiometer_drought_only"]) is True
    assert bool(drought_lc4["tensiometer_extrapolated_to_all_loadcells"]) is False
