import pandas as pd
import pytest

from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.haf_observation_operator import (
    build_harvest_observation_frame_dmc_0p056,
    dry_floor_area_to_fresh_loadcell,
    fresh_loadcell_to_dry_floor_area,
)
from stomatal_optimiaztion.domains.tomato.tomics.observers.contracts import (
    HAF_2025_2C_LOADCELL_FLOOR_AREA_M2,
)


def test_haf_harvest_observation_operator_uses_dmc_0p056() -> None:
    dry_floor = fresh_loadcell_to_dry_floor_area(1000.0)
    assert dry_floor == pytest.approx(56.0 / HAF_2025_2C_LOADCELL_FLOOR_AREA_M2)
    assert dry_floor_area_to_fresh_loadcell(dry_floor) == pytest.approx(1000.0)


def test_haf_harvest_observation_frame_marks_estimated_dry_basis() -> None:
    frame = pd.DataFrame(
        {
            "date": ["2025-11-01", "2025-11-02"],
            "loadcell_id": [1, 1],
            "treatment": ["Control", "Control"],
            "threshold_w_m2": [0, 0],
            "loadcell_daily_yield_g": [1000.0, 500.0],
            "loadcell_cumulative_yield_g": [1000.0, 1500.0],
            "fresh_yield_source": ["legacy", "legacy"],
        }
    )

    observed = build_harvest_observation_frame_dmc_0p056(frame)

    assert observed["observed_fruit_DW_g_loadcell_dmc_0p056"].tolist() == [
        56.0,
        84.0,
    ]
    assert observed["DMC_sensitivity_enabled"].eq(False).all()
    assert observed["direct_dry_yield_measured"].eq(False).all()
    assert observed["observation_operator"].eq("fresh_to_dry_dmc_0p056").all()
    assert observed["inverse_observation_operator"].eq("dry_to_fresh_dmc_0p056").all()
    assert "dmc_0p065" not in ",".join(observed.columns)
