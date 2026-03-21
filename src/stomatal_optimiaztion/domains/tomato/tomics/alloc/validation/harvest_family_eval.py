from __future__ import annotations

import copy
import math
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

import pandas as pd

from stomatal_optimiaztion.domains.tomato.tomics.alloc.components.harvest import (
    events_to_frame,
    get_fruit_harvest_policy,
    get_leaf_harvest_policy,
    run_harvest_step,
    snapshot_to_harvest_state,
    summarize_fruit_events,
    summarize_leaf_events,
)
from stomatal_optimiaztion.domains.tomato.tomics.alloc.models.tomato_legacy import (
    TomatoLegacyAdapter,
    iter_forcing_csv,
)
from stomatal_optimiaztion.domains.tomato.tomics.alloc.pipelines.tomato_legacy import (
    _policy_params_from_pipeline,
    resolve_forcing_path,
)
from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.harvest_operator import (
    model_floor_area_cumulative_total_fruit,
)
from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.metrics import (
    REPORTING_BASIS_FLOOR_AREA,
    canopy_collapse_days,
    compute_validation_bundle,
)


@dataclass(frozen=True, slots=True)
class HarvestFamilyRunResult:
    run_df: pd.DataFrame
    model_daily_df: pd.DataFrame
    validation_df: pd.DataFrame
    fruit_events_df: pd.DataFrame
    leaf_events_df: pd.DataFrame
    harvest_mass_balance_df: pd.DataFrame
    metrics: dict[str, object]


def _as_dict(raw: object) -> dict[str, Any]:
    if isinstance(raw, dict):
        return {str(key): value for key, value in raw.items()}
    return {}


def _daily_env_summary(day_rows: list[dict[str, object]], *, ec: float = 0.3) -> dict[str, float]:
    frame = pd.DataFrame(day_rows)
    summary = {
        "T_air_C": float(pd.to_numeric(frame.get("T_air_C"), errors="coerce").dropna().mean()) if "T_air_C" in frame else 23.0,
        "TF": float(pd.to_numeric(frame.get("T_air_C"), errors="coerce").dropna().mean()) if "T_air_C" in frame else 23.0,
        "EC": float(ec),
        "mature_pool_delta_g_m2": max(
            float(pd.to_numeric(frame.get("fruit_harvest_g_m2_step"), errors="coerce").fillna(0.0).sum()),
            0.0,
        )
        if "fruit_harvest_g_m2_step" in frame
        else 0.0,
        "MCFruitHar_g_m2_d": 0.0,
        "DMHar_g_m2_d": 0.0,
    }
    return summary


def _fruit_entities_to_model_cohorts(state: pd.DataFrame, *, shoots_per_m2: float) -> list[dict[str, object]]:
    if state.empty:
        return []
    frame = state.copy()
    frame["fruit_dm_g_m2"] = pd.to_numeric(frame["fruit_dm_g_m2"], errors="coerce").fillna(0.0)
    frame["fruit_count"] = pd.to_numeric(frame["fruit_count"], errors="coerce").fillna(0.0)
    frame["tdvs"] = pd.to_numeric(frame["tdvs"], errors="coerce").fillna(0.0)
    if "mult" in frame.columns:
        frame["mult"] = pd.to_numeric(frame["mult"], errors="coerce").fillna(float(shoots_per_m2))
    else:
        frame["mult"] = float(shoots_per_m2)
    frame["onplant_flag"] = frame["onplant_flag"].fillna(True).astype(bool)
    frame = frame.loc[frame["fruit_dm_g_m2"] > 1e-12].copy()
    cohorts: list[dict[str, object]] = []
    for row in frame.itertuples(index=False):
        if not bool(getattr(row, "onplant_flag", True)):
            continue
        cohorts.append(
            {
                "entity_id": str(row.entity_id),
                "tdvs": float(getattr(row, "tdvs", 0.0)),
                "n_fruits": int(max(round(float(getattr(row, "fruit_count", 0.0))), 0)),
                "w_fr_cohort": float(getattr(row, "fruit_dm_g_m2", 0.0)),
                "active": True,
                "mult": float(getattr(row, "mult", shoots_per_m2)),
            }
        )
    return cohorts


def _apply_harvest_update_to_model(
    *,
    adapter: TomatoLegacyAdapter,
    update,
) -> None:
    model = adapter.model
    if model is None:
        raise RuntimeError("TomatoLegacyAdapter model is not initialized.")
    model.W_fr_harvested = float(update.updated_state.harvested_fruit_cumulative_g_m2)
    model.last_fruit_harvest_g = float(update.fruit_harvest_flux_g_m2_d)
    model.last_leaf_harvest_g = float(update.leaf_harvest_flux_g_m2_d)
    model.truss_cohorts = _fruit_entities_to_model_cohorts(
        update.updated_state.fruit_entities,
        shoots_per_m2=float(getattr(model, "shoots_per_m2", 1.0)),
    )
    model.truss_count = len(model.truss_cohorts)
    model.W_fr = float(sum(max(float(cohort.get("w_fr_cohort", 0.0)), 0.0) for cohort in model.truss_cohorts))
    model.W_lv = max(float(getattr(model, "W_lv", 0.0)) - float(update.leaf_harvest_flux_g_m2_d), 0.0)
    if getattr(model, "fixed_lai", None) is None:
        model.LAI = max(float(update.updated_state.lai or 0.0), 0.0)
    model.vegetative_dw = float(model.W_lv + model.W_st + model.W_rt)
    model.fruit_dw = float(model.W_fr)


def _rebuild_daily_row(adapter: TomatoLegacyAdapter, current_time: pd.Timestamp, row: dict[str, object]) -> dict[str, object]:
    model = adapter.model
    if model is None:
        raise RuntimeError("TomatoLegacyAdapter model is not initialized.")
    rebuilt = dict(model.get_current_outputs(pd.Timestamp(current_time).to_pydatetime()))
    for key, value in row.items():
        rebuilt.setdefault(key, value)
    return rebuilt


def run_harvest_family_simulation(
    *,
    run_config: dict[str, Any],
    observed_df: pd.DataFrame,
    unit_label: str,
    repo_root: Path,
    fruit_harvest_family: str,
    leaf_harvest_family: str,
    fdmc_mode: str,
    fruit_params: dict[str, object] | None = None,
    leaf_params: dict[str, object] | None = None,
    plants_per_m2: float = 1.836091,
    canopy_lai_floor: float = 2.0,
    leaf_fraction_floor: float = 0.18,
) -> HarvestFamilyRunResult:
    config = copy.deepcopy(run_config)
    pipeline_cfg = _as_dict(config.get("pipeline"))
    forcing_cfg = _as_dict(config.get("forcing"))
    pipeline_cfg["internal_harvest_enabled"] = False
    config["pipeline"] = pipeline_cfg
    forcing_path = resolve_forcing_path(config, repo_root=repo_root)
    adapter = TomatoLegacyAdapter(
        fixed_lai=pipeline_cfg.get("fixed_lai"),
        partition_policy=pipeline_cfg.get("partition_policy"),
        allocation_scheme=str(pipeline_cfg.get("allocation_scheme", "4pool")),
        partition_policy_params=_policy_params_from_pipeline(pipeline_cfg),
        initial_state_overrides=_as_dict(pipeline_cfg.get("initial_state_overrides")),
        internal_harvest_enabled=False,
    )
    forcing = iter_forcing_csv(
        forcing_path,
        max_steps=forcing_cfg.get("max_steps"),
        default_dt_s=float(forcing_cfg.get("default_dt_s", 6.0 * 3600.0)),
        default_co2_ppm=float(forcing_cfg.get("default_co2_ppm", 420.0)),
        default_n_fruits_per_truss=int(forcing_cfg.get("default_n_fruits_per_truss", 4)),
    )
    resolved_fruit_params = dict(fruit_params or {})
    if fruit_harvest_family == "dekoning_fds":
        resolved_fruit_params.setdefault("fdmc_mode", fdmc_mode)
    fruit_policy = get_fruit_harvest_policy(
        fruit_harvest_family,
        resolved_fruit_params,
    )
    leaf_policy = get_leaf_harvest_policy(leaf_harvest_family, dict(leaf_params or {}))

    rows: list[dict[str, object]] = []
    fruit_events: list[object] = []
    leaf_events: list[object] = []
    mass_balance_rows: list[dict[str, object]] = []
    current_day: date | None = None
    day_rows: list[dict[str, object]] = []
    previous_daily_row: dict[str, object] | None = None

    def finalize_day() -> None:
        nonlocal day_rows, previous_daily_row, fruit_events, leaf_events
        if not day_rows:
            return
        current_row = day_rows[-1]
        state = snapshot_to_harvest_state(
            current_row,
            prior_row=previous_daily_row,
            plants_per_m2=plants_per_m2,
            floor_area_basis=True,
        )
        env = _daily_env_summary(day_rows)
        result = run_harvest_step(
            fruit_policy=fruit_policy,
            leaf_policy=leaf_policy,
            state=state,
            env=env,
            dt_days=float(state.dt_days),
        )
        _apply_harvest_update_to_model(adapter=adapter, update=result.final_update)
        rebuilt = _rebuild_daily_row(adapter, pd.Timestamp(current_row["datetime"]), current_row)
        rebuilt["fruit_harvest_family"] = fruit_harvest_family
        rebuilt["leaf_harvest_family"] = leaf_harvest_family
        rebuilt["fdmc_mode"] = fdmc_mode
        rows[-1] = rebuilt
        previous_daily_row = rebuilt
        mass_balance_rows.append(
            {
                "date": pd.Timestamp(rebuilt["datetime"]).normalize(),
                "harvest_mass_balance_error": float(result.final_update.diagnostics.get("harvest_mass_balance_error", 0.0)),
                "latent_fruit_residual_end": float(result.final_update.diagnostics.get("latent_fruit_residual_end", 0.0)),
                "leaf_harvest_mass_balance_error": float(
                    result.final_update.diagnostics.get("leaf_harvest_mass_balance_error", 0.0)
                ),
                "fruit_harvest_flux_g_m2_d": float(result.final_update.fruit_harvest_flux_g_m2_d),
                "leaf_harvest_flux_g_m2_d": float(result.final_update.leaf_harvest_flux_g_m2_d),
            }
        )
        if getattr(result.fruit_update, "diagnostics", None):
            fruit_events.extend(getattr(result.fruit_update, "diagnostics", {}).get("fruit_events", []))
        if getattr(result.leaf_update, "diagnostics", None):
            leaf_events.extend(getattr(result.leaf_update, "diagnostics", {}).get("leaf_events", []))
        day_rows = []

    for env in forcing:
        env_day = env.t.date()
        if current_day is not None and env_day != current_day:
            finalize_day()
        outputs = dict(adapter.step(env))
        row = {"datetime": env.t, **outputs}
        row["fruit_harvest_family"] = fruit_harvest_family
        row["leaf_harvest_family"] = leaf_harvest_family
        row["fdmc_mode"] = fdmc_mode
        rows.append(row)
        day_rows.append(row)
        current_day = env_day
    finalize_day()

    run_df = pd.DataFrame(rows)
    fruit_events_df = events_to_frame(fruit_events)
    leaf_events_df = events_to_frame(leaf_events)
    harvest_mass_balance_df = pd.DataFrame(mass_balance_rows)
    model_daily_df = model_floor_area_cumulative_total_fruit(run_df)
    indexed = model_daily_df.set_index("date")
    candidate_series = observed_df["date"].map(indexed["model_cumulative_total_fruit_dry_weight_floor_area"])
    candidate_daily_increment = observed_df["date"].map(indexed["model_daily_increment_floor_area"])
    bundle = compute_validation_bundle(
        observed_df.copy(),
        candidate_series=candidate_series,
        candidate_daily_increment_series=candidate_daily_increment,
        candidate_label="model",
        unit_declared_in_observation_file=unit_label,
    )
    event_summary = summarize_fruit_events(fruit_events)
    leaf_summary = summarize_leaf_events(leaf_events)
    metrics: dict[str, object] = {
        **bundle.metrics,
        **event_summary,
        **leaf_summary,
        "reporting_basis": REPORTING_BASIS_FLOOR_AREA,
        "fruit_harvest_family": fruit_harvest_family,
        "leaf_harvest_family": leaf_harvest_family,
        "fdmc_mode": fdmc_mode,
        "harvest_mass_balance_error": float(
            pd.to_numeric(harvest_mass_balance_df.get("harvest_mass_balance_error"), errors="coerce").fillna(0.0).max()
        )
        if not harvest_mass_balance_df.empty
        else 0.0,
        "latent_fruit_residual_end": float(
            pd.to_numeric(harvest_mass_balance_df.get("latent_fruit_residual_end"), errors="coerce").fillna(0.0).iloc[-1]
        )
        if not harvest_mass_balance_df.empty
        else 0.0,
        "leaf_harvest_mass_balance_error": float(
            pd.to_numeric(harvest_mass_balance_df.get("leaf_harvest_mass_balance_error"), errors="coerce").fillna(0.0).max()
        )
        if not harvest_mass_balance_df.empty
        else 0.0,
        "final_lai": float(pd.to_numeric(run_df.get("LAI"), errors="coerce").dropna().iloc[-1]) if "LAI" in run_df else math.nan,
        "canopy_collapse_days": canopy_collapse_days(run_df, lai_floor=canopy_lai_floor, leaf_floor=leaf_fraction_floor),
        "final_fruit_dry_weight_floor_area": float(
            pd.to_numeric(model_daily_df["model_cumulative_harvested_fruit_dry_weight_floor_area"], errors="coerce")
            .dropna()
            .iloc[-1]
        )
        if not model_daily_df.empty
        else math.nan,
    }
    return HarvestFamilyRunResult(
        run_df=run_df,
        model_daily_df=model_daily_df,
        validation_df=bundle.merged_df,
        fruit_events_df=fruit_events_df,
        leaf_events_df=leaf_events_df,
        harvest_mass_balance_df=harvest_mass_balance_df,
        metrics=metrics,
    )


def build_harvest_overlay_frame(validation_df: pd.DataFrame, *, source_label: str = "model") -> pd.DataFrame:
    return pd.DataFrame(
        {
            "datetime": pd.to_datetime(validation_df["date"], errors="coerce"),
            "cumulative_total_fruit_floor_area": pd.to_numeric(
                validation_df[f"{source_label}_cumulative_total_fruit_dry_weight_floor_area"],
                errors="coerce",
            ),
            "offset_adjusted_cumulative_total_fruit_floor_area": pd.to_numeric(
                validation_df[f"{source_label}_offset_adjusted"],
                errors="coerce",
            ),
            "daily_increment_floor_area": pd.to_numeric(
                validation_df[f"{source_label}_daily_increment_floor_area"],
                errors="coerce",
            ),
        }
    )


def build_harvest_mass_balance_overlay_frame(harvest_mass_balance_df: pd.DataFrame) -> pd.DataFrame:
    frame = harvest_mass_balance_df.copy()
    if frame.empty:
        return pd.DataFrame(
            columns=[
                "datetime",
                "cumulative_total_fruit_floor_area",
                "offset_adjusted_cumulative_total_fruit_floor_area",
                "daily_increment_floor_area",
            ]
        )
    return pd.DataFrame(
        {
            "datetime": pd.to_datetime(frame["date"], errors="coerce"),
            "cumulative_total_fruit_floor_area": pd.to_numeric(frame["harvest_mass_balance_error"], errors="coerce"),
            "offset_adjusted_cumulative_total_fruit_floor_area": pd.to_numeric(
                frame["latent_fruit_residual_end"],
                errors="coerce",
            ),
            "daily_increment_floor_area": pd.to_numeric(frame["leaf_harvest_mass_balance_error"], errors="coerce"),
        }
    )


__all__ = [
    "HarvestFamilyRunResult",
    "build_harvest_mass_balance_overlay_frame",
    "build_harvest_overlay_frame",
    "run_harvest_family_simulation",
]
