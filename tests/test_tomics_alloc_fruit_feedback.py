from __future__ import annotations

import pytest

from stomatal_optimiaztion.domains.tomato.tomics.alloc.components.partitioning.fruit_feedback import (
    apply_fruit_feedback_mode,
    apply_fruit_feedback_proxy,
)
from stomatal_optimiaztion.domains.tomato.tomics.alloc.components.partitioning.research_modes import (
    ResearchArchitectureConfig,
)


def test_fruit_feedback_is_inactive_when_mode_is_off() -> None:
    result = apply_fruit_feedback_mode(
        config=ResearchArchitectureConfig(fruit_feedback_mode="off"),
        fruit_fraction=0.45,
        supply_demand_ratio=0.6,
        fruit_load_pressure=0.8,
    )

    assert result.fruit_fraction == pytest.approx(0.45, abs=1e-12)
    assert result.fruit_abort_fraction == pytest.approx(0.0, abs=1e-12)
    assert result.fruit_set_feedback_events == 0


def test_tomgro_feedback_reduces_fruit_sink_when_supply_is_limiting() -> None:
    sinks, abort_fraction, events = apply_fruit_feedback_proxy(
        mode="tomgro_abort_proxy",
        sinks={"S_fr_g_d": 7.0, "S_veg_g_d": 3.0},
        supply_dm_equivalent_g_d=2.0,
        active_trusses=4,
        threshold=0.8,
        slope=1.5,
    )

    assert sinks["S_fr_g_d"] < 7.0
    assert abort_fraction > 0.0
    assert events >= 1
