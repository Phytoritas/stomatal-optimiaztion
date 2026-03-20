from __future__ import annotations

import pytest

from stomatal_optimiaztion.domains.tomato.tomics.alloc.components.partitioning.research_modes import (
    ResearchArchitectureConfig,
)
from stomatal_optimiaztion.domains.tomato.tomics.alloc.components.partitioning.reserve_buffer import (
    apply_reserve_buffer_mode,
    resolve_realized_growth_with_buffer,
)


def test_storage_pool_changes_accounting_only_when_enabled() -> None:
    off = resolve_realized_growth_with_buffer(
        mode="off",
        net_ch2o_step_g=6.0,
        c_f=0.7,
        cap_dm_step=3.0,
        reserve_pool_g=2.0,
        buffer_pool_g=0.0,
        storage_capacity_g=20.0,
        storage_carryover_fraction=1.0,
        buffer_capacity_g=0.0,
        buffer_min_fraction=0.0,
    )
    storage = resolve_realized_growth_with_buffer(
        mode="tomsim_storage_pool",
        net_ch2o_step_g=6.0,
        c_f=0.7,
        cap_dm_step=3.0,
        reserve_pool_g=2.0,
        buffer_pool_g=0.0,
        storage_capacity_g=8.0,
        storage_carryover_fraction=0.5,
        buffer_capacity_g=0.0,
        buffer_min_fraction=0.0,
    )

    assert off[0] == pytest.approx(storage[0], abs=1e-9)
    assert off[1] != pytest.approx(storage[1], abs=1e-9)


def test_vanthoor_buffer_path_only_uses_buffer_when_enabled() -> None:
    result = apply_reserve_buffer_mode(
        config=ResearchArchitectureConfig(
            reserve_buffer_mode="vanthoor_carbohydrate_buffer",
            temporal_coupling_mode="buffered_daily",
            buffer_capacity_g_m2=12.0,
            buffer_min_fraction=0.10,
            buffer_release_rate_g_m2_d=6.0,
        ),
        net_ch2o_step_g=5.0,
        required_ch2o_g=4.0,
        reserve_pool_g=0.0,
        buffer_pool_g=0.0,
        dt_s=86400.0,
    )

    assert result.reserve_pool_g == pytest.approx(0.0, abs=1e-9)
    assert result.buffer_pool_g > 0.0
    assert result.buffer_fill_g > 0.0
    assert result.buffer_draw_g > 0.0
