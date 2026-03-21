from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

import pandas as pd

from .contracts import (
    FRUIT_ENTITY_COLUMNS,
    LEAF_ENTITY_COLUMNS,
    FruitHarvestEvent,
    HarvestPolicy,
    HarvestState,
    HarvestUpdate,
    LeafHarvestEvent,
    LeafHarvestPolicy,
    ensure_entity_frame,
)
from .diagnostics import event_diagnostics, state_scalar_diagnostics
from .mass_balance import mass_balance_metrics


@dataclass(frozen=True, slots=True)
class CombinedHarvestResult:
    fruit_update: HarvestUpdate
    leaf_update: HarvestUpdate
    final_update: HarvestUpdate


def _apply_fruit_events(
    frame: pd.DataFrame,
    events: list[FruitHarvestEvent],
) -> pd.DataFrame:
    updated = ensure_entity_frame(frame, FRUIT_ENTITY_COLUMNS)
    if updated.empty or not events:
        return updated
    updated = updated.copy()
    updated["fruit_dm_g_m2"] = pd.to_numeric(updated["fruit_dm_g_m2"], errors="coerce").fillna(0.0)
    for event in events:
        mask = updated["entity_id"].astype(str).eq(str(event.entity_id))
        if not mask.any():
            continue
        available = float(updated.loc[mask, "fruit_dm_g_m2"].iloc[0])
        harvested = min(max(float(event.dry_weight_g_m2), 0.0), max(available, 0.0))
        updated.loc[mask, "fruit_dm_g_m2"] = max(available - harvested, 0.0)
        updated.loc[mask, "onplant_flag"] = False
        updated.loc[mask, "harvested_flag"] = True
    return updated


def _apply_leaf_events(
    frame: pd.DataFrame,
    events: list[LeafHarvestEvent],
) -> tuple[pd.DataFrame, float]:
    updated = ensure_entity_frame(frame, LEAF_ENTITY_COLUMNS)
    if updated.empty or not events:
        return updated, 0.0
    updated = updated.copy()
    updated["leaf_dm_g_m2"] = pd.to_numeric(updated["leaf_dm_g_m2"], errors="coerce").fillna(0.0)
    updated["leaf_area_m2_m2"] = pd.to_numeric(updated["leaf_area_m2_m2"], errors="coerce").fillna(0.0)
    lai_removed = 0.0
    for event in events:
        mask = updated["entity_id"].astype(str).eq(str(event.entity_id))
        if not mask.any():
            continue
        available_dm = float(updated.loc[mask, "leaf_dm_g_m2"].iloc[0])
        available_area = float(updated.loc[mask, "leaf_area_m2_m2"].iloc[0])
        removed_dm = min(max(float(event.leaf_harvest_flux_g_m2), 0.0), max(available_dm, 0.0))
        fraction = 0.0 if available_dm <= 1e-12 else min(max(removed_dm / available_dm, 0.0), 1.0)
        removed_area = available_area * fraction
        updated.loc[mask, "leaf_dm_g_m2"] = max(available_dm - removed_dm, 0.0)
        updated.loc[mask, "leaf_area_m2_m2"] = max(available_area - removed_area, 0.0)
        updated.loc[mask, "onplant_flag"] = False if fraction >= 0.999999 else True
        updated.loc[mask, "harvested_flag"] = True if fraction >= 0.999999 else False
        lai_removed += removed_area
    return updated, lai_removed


def build_harvest_update(
    state: HarvestState,
    *,
    fruit_events: list[FruitHarvestEvent] | None = None,
    leaf_events: list[LeafHarvestEvent] | None = None,
    extra_diagnostics: dict[str, float | int | str | bool] | None = None,
) -> HarvestUpdate:
    fruit_events = list(fruit_events or [])
    leaf_events = list(leaf_events or [])
    updated_fruit = _apply_fruit_events(state.fruit_entities, fruit_events)
    updated_leaf, lai_removed = _apply_leaf_events(state.leaf_entities, leaf_events)
    updated_state = state.with_updates(
        fruit_entities=updated_fruit,
        leaf_entities=updated_leaf,
        harvested_fruit_cumulative_g_m2=(
            float(state.harvested_fruit_cumulative_g_m2)
            + sum(max(float(event.dry_weight_g_m2), 0.0) for event in fruit_events)
        ),
        harvested_leaf_cumulative_g_m2=(
            float(state.harvested_leaf_cumulative_g_m2)
            + sum(max(float(event.leaf_harvest_flux_g_m2), 0.0) for event in leaf_events)
        ),
        lai=max(float(state.lai or 0.0) - lai_removed, 0.0) if state.lai is not None else None,
    )
    diagnostics: dict[str, Any] = {
        **state_scalar_diagnostics(updated_state),
        **event_diagnostics(fruit_events, leaf_events),
        **mass_balance_metrics(
            state,
            updated_state,
            fruit_events=fruit_events,
            leaf_events=leaf_events,
        ),
        **dict(extra_diagnostics or {}),
    }
    diagnostics["fruit_events"] = fruit_events
    diagnostics["leaf_events"] = leaf_events
    return HarvestUpdate(
        updated_state=updated_state,
        fruit_harvest_flux_g_m2_d=float(sum(max(float(event.dry_weight_g_m2), 0.0) for event in fruit_events)),
        leaf_harvest_flux_g_m2_d=float(sum(max(float(event.leaf_harvest_flux_g_m2), 0.0) for event in leaf_events)),
        fruit_harvest_event_count=len(fruit_events),
        leaf_harvest_event_count=len(leaf_events),
        mass_balance_error=float(diagnostics["harvest_mass_balance_error"]),
        diagnostics=diagnostics,
    )


def run_harvest_step(
    *,
    fruit_policy: HarvestPolicy,
    leaf_policy: LeafHarvestPolicy,
    state: HarvestState,
    env: dict[str, float],
    dt_days: float,
) -> CombinedHarvestResult:
    fruit_update = fruit_policy.step(state, env, dt_days)
    leaf_env = {
        **env,
        "truss_stage_lookup": {
            str(row["truss_id"]): float(row["tdvs"])
            for _, row in fruit_update.updated_state.fruit_entities.iterrows()
            if pd.notna(row.get("truss_id")) and pd.notna(row.get("tdvs"))
        },
    }
    leaf_update = leaf_policy.step(fruit_update.updated_state, leaf_env, dt_days)
    final_update = HarvestUpdate(
        updated_state=leaf_update.updated_state,
        fruit_harvest_flux_g_m2_d=fruit_update.fruit_harvest_flux_g_m2_d,
        leaf_harvest_flux_g_m2_d=leaf_update.leaf_harvest_flux_g_m2_d,
        fruit_harvest_event_count=fruit_update.fruit_harvest_event_count,
        leaf_harvest_event_count=leaf_update.leaf_harvest_event_count,
        mass_balance_error=max(float(fruit_update.mass_balance_error), float(leaf_update.mass_balance_error)),
        diagnostics={**fruit_update.diagnostics, **leaf_update.diagnostics},
    )
    return CombinedHarvestResult(
        fruit_update=fruit_update,
        leaf_update=leaf_update,
        final_update=final_update,
    )


def replay_harvest_updates(
    *,
    states: list[HarvestState],
    fruit_policy: HarvestPolicy,
    leaf_policy: LeafHarvestPolicy,
    env_rows: list[dict[str, float]] | None = None,
) -> list[HarvestUpdate]:
    env_rows = env_rows or [{} for _ in states]
    return [
        run_harvest_step(
            fruit_policy=fruit_policy,
            leaf_policy=leaf_policy,
            state=state,
            env=env_rows[min(index, len(env_rows) - 1)],
            dt_days=float(state.dt_days),
        ).final_update
        for index, state in enumerate(states)
    ]


def events_to_frame(events: list[FruitHarvestEvent] | list[LeafHarvestEvent]) -> pd.DataFrame:
    return pd.DataFrame([asdict(event) for event in events])


def summarize_fruit_events(events: list[FruitHarvestEvent]) -> dict[str, float]:
    if not events:
        return {
            "fruit_harvest_event_count": 0.0,
            "fruit_harvest_flux_g_m2_d": 0.0,
            "mean_harvest_weight_dry": 0.0,
            "mean_harvest_weight_fresh": 0.0,
            "mean_harvest_fdmc": 0.0,
        }
    dry_weights = pd.Series([max(float(event.dry_weight_g_m2), 0.0) for event in events], dtype=float)
    fresh_weights = pd.Series(
        [float(event.fresh_weight_equivalent_g_m2) for event in events if event.fresh_weight_equivalent_g_m2 is not None],
        dtype=float,
    )
    fdmc_values = pd.Series([float(event.fdmc_used) for event in events if event.fdmc_used is not None], dtype=float)
    return {
        "fruit_harvest_event_count": float(len(events)),
        "fruit_harvest_flux_g_m2_d": float(dry_weights.sum()),
        "mean_harvest_weight_dry": float(dry_weights.mean()),
        "mean_harvest_weight_fresh": float(fresh_weights.mean()) if not fresh_weights.empty else 0.0,
        "mean_harvest_fdmc": float(fdmc_values.mean()) if not fdmc_values.empty else 0.0,
    }


def summarize_leaf_events(events: list[LeafHarvestEvent]) -> dict[str, float]:
    if not events:
        return {"leaf_harvest_event_count": 0.0, "leaf_harvest_flux_g_m2_d": 0.0}
    fluxes = pd.Series([max(float(event.leaf_harvest_flux_g_m2), 0.0) for event in events], dtype=float)
    return {
        "leaf_harvest_event_count": float(len(events)),
        "leaf_harvest_flux_g_m2_d": float(fluxes.sum()),
    }


__all__ = [
    "CombinedHarvestResult",
    "build_harvest_update",
    "events_to_frame",
    "replay_harvest_updates",
    "run_harvest_step",
    "summarize_fruit_events",
    "summarize_leaf_events",
]
