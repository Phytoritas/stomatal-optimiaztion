import pytest

from stomatal_optimiaztion.domains.tomato.tomics.observers.contracts import (
    HAF_2025_2C_LOADCELL_FLOOR_AREA_M2,
)
from stomatal_optimiaztion.domains.tomato.tomics.observers.yield_bridge import (
    dry_floor_area_to_fresh_loadcell,
    dry_g_to_fresh_g,
    fresh_g_to_dry_g,
    fresh_loadcell_to_dry_floor_area,
)


def test_haf_2025_2c_fresh_dry_conversions_use_0p056() -> None:
    assert fresh_g_to_dry_g(1000.0) == pytest.approx(56.0)
    assert fresh_loadcell_to_dry_floor_area(1000.0) == pytest.approx(56.0 / HAF_2025_2C_LOADCELL_FLOOR_AREA_M2)
    assert dry_g_to_fresh_g(56.0) == pytest.approx(1000.0)
    assert dry_floor_area_to_fresh_loadcell(56.0 / HAF_2025_2C_LOADCELL_FLOOR_AREA_M2) == pytest.approx(1000.0)
