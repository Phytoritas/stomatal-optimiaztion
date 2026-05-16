import pandas as pd

from stomatal_optimiaztion.domains.tomato.tomics.observers.feature_frame import build_observer_feature_frame


def test_observer_feature_frame_flags_unavailable_lai_yield_and_indirect_allocation() -> None:
    frame = build_observer_feature_frame(
        daily_et_wide=pd.DataFrame(
            {
                "date": ["2025-12-14"],
                "loadcell_id": [1],
                "treatment": ["Control"],
                "threshold_w_m2": [0.0],
                "radiation_day_ET_g": [10.0],
                "radiation_night_ET_g": [2.0],
            }
        ),
        rootzone_indices=pd.DataFrame(
            {
                "date": ["2025-12-14"],
                "loadcell_id": [1],
                "treatment": ["Control"],
                "RZI_main": [0.0],
                "apparent_canopy_conductance": [5.0],
                "apparent_canopy_conductance_available": [True],
            }
        ),
    )

    row = frame.iloc[0]
    assert bool(row["LAI_available"]) is False
    assert bool(row["fresh_yield_available"]) is False
    assert bool(row["dry_yield_available"]) is False
    assert row["canonical_fruit_DMC_fraction"] == 0.056
    assert row["fruit_DMC_fraction"] == 0.056
    assert row["default_fruit_dry_matter_content"] == 0.056
    assert bool(row["DMC_fixed_for_2025_2C"]) is True
    assert bool(row["DMC_sensitivity_enabled"]) is False
    assert bool(row["dry_yield_is_dmc_estimated"]) is False
    assert bool(row["direct_dry_yield_measured"]) is False
    assert bool(row["direct_partition_observation_available"]) is False
    assert row["allocation_validation_basis"] == "indirect_observer_features_only"
