from __future__ import annotations

import pandas as pd

from stomatal_optimiaztion.domains.tomato.tomics.alloc.components.harvest.contracts import (
    FruitHarvestEvent,
    HarvestState,
    LeafHarvestEvent,
)


def state_scalar_diagnostics(state: HarvestState) -> dict[str, float]:
    fruit_dm = pd.to_numeric(state.fruit_entities.get("fruit_dm_g_m2"), errors="coerce").fillna(0.0)
    leaf_dm = pd.to_numeric(state.leaf_entities.get("leaf_dm_g_m2"), errors="coerce").fillna(0.0)
    return {
        "fruit_entity_count": float(state.fruit_entities.shape[0]),
        "leaf_entity_count": float(state.leaf_entities.shape[0]),
        "latent_fruit_mass_g_m2": float(fruit_dm.sum()),
        "latent_leaf_mass_g_m2": float(leaf_dm.sum()),
        "harvested_fruit_cumulative_g_m2": float(state.harvested_fruit_cumulative_g_m2),
        "harvested_leaf_cumulative_g_m2": float(state.harvested_leaf_cumulative_g_m2),
    }


def event_diagnostics(
    fruit_events: list[FruitHarvestEvent],
    leaf_events: list[LeafHarvestEvent],
) -> dict[str, float]:
    return {
        "fruit_harvest_event_count": float(len(fruit_events)),
        "leaf_harvest_event_count": float(len(leaf_events)),
        "fruit_harvest_flux_g_m2_d": float(sum(event.dry_weight_g_m2 for event in fruit_events)),
        "leaf_harvest_flux_g_m2_d": float(sum(event.leaf_harvest_flux_g_m2 for event in leaf_events)),
    }


__all__ = ["event_diagnostics", "state_scalar_diagnostics"]
