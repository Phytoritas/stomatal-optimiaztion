from __future__ import annotations

from dataclasses import dataclass

from stomatal_optimiaztion.domains.tomato.tomics.alloc.components.partitioning.research_modes import (
    ResearchArchitectureConfig,
)


@dataclass(frozen=True, slots=True)
class FruitFeedbackResult:
    fruit_fraction: float
    fruit_abort_fraction: float
    fruit_set_feedback_events: int


def apply_fruit_feedback_mode(
    *,
    config: ResearchArchitectureConfig,
    fruit_fraction: float,
    supply_demand_ratio: float,
    fruit_load_pressure: float,
) -> FruitFeedbackResult:
    fruit_fraction = max(float(fruit_fraction), 0.0)
    ratio = max(min(float(supply_demand_ratio), 1.5), 0.0)
    pressure = max(float(fruit_load_pressure), 0.0)

    if config.fruit_feedback_mode == "off":
        return FruitFeedbackResult(
            fruit_fraction=fruit_fraction,
            fruit_abort_fraction=0.0,
            fruit_set_feedback_events=0,
        )

    threshold = max(min(config.fruit_abort_threshold, 1.0), 0.0)
    slope = max(config.fruit_abort_slope, 0.0)
    stress_gap = max(threshold - ratio, 0.0)
    if config.fruit_feedback_mode == "tomgro_abort_proxy":
        abort_fraction = min(stress_gap * slope, 0.45)
    else:
        abort_fraction = min(stress_gap * slope * max(pressure, 1.0), 0.35)

    adjusted = fruit_fraction * (1.0 - abort_fraction)
    return FruitFeedbackResult(
        fruit_fraction=max(adjusted, 0.0),
        fruit_abort_fraction=abort_fraction,
        fruit_set_feedback_events=int(abort_fraction > 1e-9),
    )


def apply_fruit_feedback_proxy(
    *,
    mode: str,
    sinks: dict[str, float],
    supply_dm_equivalent_g_d: float,
    active_trusses: int,
    threshold: float,
    slope: float,
) -> tuple[dict[str, float], float, int]:
    total_demand = max(float(sinks.get("S_fr_g_d", 0.0)) + float(sinks.get("S_veg_g_d", 0.0)), 1e-9)
    fruit_fraction = max(float(sinks.get("S_fr_g_d", 0.0)) / total_demand, 0.0)
    result = apply_fruit_feedback_mode(
        config=ResearchArchitectureConfig(
            fruit_feedback_mode=str(mode),
            fruit_abort_threshold=float(threshold),
            fruit_abort_slope=float(slope),
        ),
        fruit_fraction=fruit_fraction,
        supply_demand_ratio=float(supply_dm_equivalent_g_d) / total_demand,
        fruit_load_pressure=max(active_trusses, 1) * fruit_fraction,
    )
    adjusted_total_fruit = result.fruit_fraction * total_demand
    adjusted_sinks = {
        "S_fr_g_d": adjusted_total_fruit,
        "S_veg_g_d": max(total_demand - adjusted_total_fruit, 1e-9),
    }
    return adjusted_sinks, result.fruit_abort_fraction, result.fruit_set_feedback_events
