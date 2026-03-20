from __future__ import annotations

from dataclasses import dataclass

from stomatal_optimiaztion.domains.tomato.tomics.alloc.components.partitioning.research_modes import (
    ResearchArchitectureConfig,
)


@dataclass(frozen=True, slots=True)
class ReserveBufferResult:
    available_ch2o_g: float
    reserve_pool_g: float
    buffer_pool_g: float
    reserve_fill_g: float
    reserve_draw_g: float
    buffer_fill_g: float
    buffer_draw_g: float


def apply_reserve_buffer_mode(
    *,
    config: ResearchArchitectureConfig,
    net_ch2o_step_g: float,
    required_ch2o_g: float,
    reserve_pool_g: float,
    buffer_pool_g: float,
    dt_s: float,
) -> ReserveBufferResult:
    supply = max(float(net_ch2o_step_g), 0.0)
    required = max(float(required_ch2o_g), 0.0)
    reserve_pool = max(float(reserve_pool_g), 0.0)
    buffer_pool = max(float(buffer_pool_g), 0.0)

    if config.reserve_buffer_mode == "off":
        return ReserveBufferResult(
            available_ch2o_g=supply,
            reserve_pool_g=reserve_pool,
            buffer_pool_g=buffer_pool,
            reserve_fill_g=0.0,
            reserve_draw_g=0.0,
            buffer_fill_g=0.0,
            buffer_draw_g=0.0,
        )

    if config.reserve_buffer_mode == "tomsim_storage_pool":
        reserve_capacity = max(config.reserve_capacity_g_m2, 0.0)
        carryover = min(max(config.reserve_carryover_fraction, 0.0), 1.0)
        reserve_pool *= carryover
        available = supply + reserve_pool
        used = min(required, available)
        reserve_draw = min(max(used - supply, 0.0), reserve_pool)
        reserve_after_draw = max(0.0, reserve_pool - reserve_draw)
        reserve_fill = min(max(available - used, 0.0), max(0.0, reserve_capacity - reserve_after_draw))
        reserve_pool = reserve_after_draw + reserve_fill
        return ReserveBufferResult(
            available_ch2o_g=available,
            reserve_pool_g=reserve_pool,
            buffer_pool_g=0.0,
            reserve_fill_g=reserve_fill,
            reserve_draw_g=reserve_draw,
            buffer_fill_g=0.0,
            buffer_draw_g=0.0,
        )

    buffer_capacity = max(config.buffer_capacity_g_m2, 0.0)
    buffer_min = min(max(config.buffer_min_fraction, 0.0), 0.95) * buffer_capacity
    release_cap = max(config.buffer_release_rate_g_m2_d, 0.0) * (max(float(dt_s), 0.0) / 86400.0)

    buffer_fill = min(max(supply, 0.0), max(0.0, buffer_capacity - buffer_pool))
    buffer_pool += buffer_fill

    releasable = max(0.0, buffer_pool - buffer_min)
    buffer_draw = min(required, releasable, release_cap if release_cap > 0 else releasable)
    buffer_pool = max(buffer_min, buffer_pool - buffer_draw)

    return ReserveBufferResult(
        available_ch2o_g=buffer_draw,
        reserve_pool_g=reserve_pool,
        buffer_pool_g=buffer_pool,
        reserve_fill_g=0.0,
        reserve_draw_g=0.0,
        buffer_fill_g=buffer_fill,
        buffer_draw_g=buffer_draw,
    )


def resolve_realized_growth_with_buffer(
    *,
    mode: str,
    net_ch2o_step_g: float,
    c_f: float,
    cap_dm_step: float,
    reserve_pool_g: float,
    buffer_pool_g: float,
    storage_capacity_g: float,
    storage_carryover_fraction: float,
    buffer_capacity_g: float,
    buffer_min_fraction: float,
) -> tuple[float, float, float]:
    if c_f <= 1e-12:
        return 0.0, max(float(reserve_pool_g), 0.0), max(float(buffer_pool_g), 0.0)
    if str(mode).strip().lower() == "off":
        available_ch2o_g = max(float(net_ch2o_step_g), 0.0)
        dW_total_step = min(max(float(cap_dm_step), 0.0), float(c_f) * available_ch2o_g)
        return dW_total_step, max(float(reserve_pool_g), 0.0), max(float(buffer_pool_g), 0.0)

    required_ch2o_g = max(float(cap_dm_step), 0.0) / float(c_f)
    config = ResearchArchitectureConfig(
        reserve_buffer_mode=str(mode),
        reserve_capacity_g_m2=max(float(storage_capacity_g), 0.0),
        reserve_carryover_fraction=float(storage_carryover_fraction),
        buffer_capacity_g_m2=max(float(buffer_capacity_g), 0.0),
        buffer_min_fraction=float(buffer_min_fraction),
    )
    result = apply_reserve_buffer_mode(
        config=config,
        net_ch2o_step_g=float(net_ch2o_step_g),
        required_ch2o_g=required_ch2o_g,
        reserve_pool_g=float(reserve_pool_g),
        buffer_pool_g=float(buffer_pool_g),
        dt_s=86400.0,
    )
    available = max(float(result.available_ch2o_g), 0.0)
    dW_total_step = min(max(float(cap_dm_step), 0.0), float(c_f) * available)
    return dW_total_step, result.reserve_pool_g, result.buffer_pool_g
