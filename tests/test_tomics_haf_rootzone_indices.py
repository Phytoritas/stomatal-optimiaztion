import pandas as pd
import pytest

from stomatal_optimiaztion.domains.tomato.tomics.observers.rootzone_indices import build_rootzone_indices


def test_rzi_sign_and_apparent_conductance_direction() -> None:
    dataset2 = pd.DataFrame(
        {
            "date": ["2025-12-14", "2025-12-14"],
            "loadcell_id": [1, 4],
            "treatment": ["Control", "Drought"],
            "moisture_percent": [80.0, 40.0],
            "ec_ds": [2.0, 3.0],
            "tensiometer_hp": [1.0, 2.0],
        }
    )
    daily_et = pd.DataFrame(
        {
            "date": ["2025-12-14", "2025-12-14"],
            "loadcell_id": [1, 4],
            "treatment": ["Control", "Drought"],
            "radiation_total_ET_g": [20.0, 10.0],
            "env_vpd_kpa_mean": [2.0, 2.0],
        }
    )

    rootzone = build_rootzone_indices(dataset2, daily_et)
    drought = rootzone[rootzone["loadcell_id"].eq(4)].iloc[0]

    assert drought["RZI_theta_paired"] > 0
    assert drought["RZI_theta_paired"] == 0.50000000000625
    assert drought["apparent_canopy_conductance"] == pytest.approx(5.0)
