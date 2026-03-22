from __future__ import annotations

import json
from collections.abc import Mapping

import pandas as pd

from .contracts import FRUIT_ENTITY_COLUMNS, LEAF_ENTITY_COLUMNS, HarvestState, ensure_entity_frame


def _as_series(row: pd.Series | Mapping[str, object] | None) -> pd.Series | None:
    if row is None:
        return None
    if isinstance(row, pd.Series):
        return row
    return pd.Series(dict(row))


def _float_from(series: pd.Series, key: str, default: float = 0.0) -> float:
    value = series.get(key, default)
    numeric = pd.to_numeric(pd.Series([value]), errors="coerce").iloc[0]
    return float(default if pd.isna(numeric) else numeric)


def _bool_from(value: object, default: bool) -> bool:
    if value is None or value is pd.NA:
        return bool(default)
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"true", "1", "yes"}:
            return True
        if lowered in {"false", "0", "no"}:
            return False
    try:
        return bool(value)
    except Exception:
        return bool(default)


def _int_stage_from_tdvs(tdvs: float, *, max_stage: int) -> int:
    return int(min(max_stage, max(1, round(max(tdvs, 0.0) * max_stage))))


def _prior_fruit_lookup(prior_row: pd.Series | None) -> pd.DataFrame:
    if prior_row is None:
        return pd.DataFrame(columns=FRUIT_ENTITY_COLUMNS)
    payload = prior_row.get("__harvest_state_fruit_entities")
    if isinstance(payload, pd.DataFrame):
        return ensure_entity_frame(payload, FRUIT_ENTITY_COLUMNS)
    prior_json = prior_row.get("truss_cohorts_json", "")
    if not isinstance(prior_json, str) or not prior_json.strip():
        return pd.DataFrame(columns=FRUIT_ENTITY_COLUMNS)
    try:
        parsed = json.loads(prior_json)
    except json.JSONDecodeError:
        parsed = []
    if not isinstance(parsed, list):
        return pd.DataFrame(columns=FRUIT_ENTITY_COLUMNS)
    return ensure_entity_frame(pd.DataFrame([row for row in parsed if isinstance(row, dict)]), FRUIT_ENTITY_COLUMNS)


def _merge_prior_runtime_fields(frame: pd.DataFrame, prior_frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty or prior_frame.empty or "entity_id" not in frame.columns or "entity_id" not in prior_frame.columns:
        return frame
    prior_indexed = prior_frame.copy()
    prior_indexed["entity_id"] = prior_indexed["entity_id"].astype(str)
    prior_indexed = prior_indexed.set_index("entity_id")
    runtime_columns = [
        "sink_active_flag",
        "mature_flag",
        "harvest_ready_flag",
        "onplant_flag",
        "harvested_flag",
        "anthesis_at",
        "matured_at",
        "days_since_anthesis",
        "days_since_maturity",
        "mature_pool_flag",
        "mature_pool_residence_days",
        "final_stage_flag",
        "final_stage_residence_days",
        "explicit_outflow_capacity_g_m2_d",
        "proxy_state_flag",
    ]
    out = frame.copy()
    out["entity_id"] = out["entity_id"].astype(str)
    for column in runtime_columns:
        if column not in out.columns:
            out[column] = pd.NA
        mapped = out["entity_id"].map(prior_indexed[column]) if column in prior_indexed.columns else pd.Series(pd.NA, index=out.index)
        out[column] = out[column].where(out[column].notna(), mapped)
    return out


def _clip_series(series: pd.Series, *, lower: float = 0.0, upper: float | None = None) -> pd.Series:
    out = pd.to_numeric(series, errors="coerce").fillna(lower)
    out = out.clip(lower=lower)
    if upper is not None:
        out = out.clip(upper=upper)
    return out


def _distribution_json(series: pd.Series) -> str:
    if series is None or series.empty:
        return json.dumps({}, sort_keys=True)
    cleaned = series.dropna().astype(str)
    if cleaned.empty:
        return json.dumps({}, sort_keys=True)
    counts = cleaned.value_counts(normalize=True).sort_index()
    return json.dumps({str(key): float(value) for key, value in counts.items()}, sort_keys=True)


def _timestamp_or_none(value: object) -> str | None:
    if isinstance(value, str) and value.strip():
        return value
    ts = pd.to_datetime(value, errors="coerce")
    if pd.isna(ts):
        return None
    return ts.isoformat()


def _timestamp_from_days(current_time: pd.Timestamp, days: float) -> str | None:
    days = max(float(days), 0.0)
    if pd.isna(current_time) or days <= 0.0:
        return None
    return (current_time - pd.to_timedelta(days, unit="D")).isoformat()


def _prepare_runtime_clock_fields(frame: pd.DataFrame, *, current_time: pd.Timestamp) -> pd.DataFrame:
    out = frame.copy()
    out["days_since_anthesis"] = _clip_series(out.get("days_since_anthesis"), lower=0.0)
    out["days_since_maturity"] = _clip_series(out.get("days_since_maturity"), lower=0.0)
    out["anthesis_at"] = out.get("anthesis_at").map(_timestamp_or_none)
    out["matured_at"] = out.get("matured_at").map(_timestamp_or_none)
    missing_anthesis = out["anthesis_at"].isna() & out["days_since_anthesis"].gt(0.0)
    out.loc[missing_anthesis, "anthesis_at"] = out.loc[missing_anthesis, "days_since_anthesis"].map(
        lambda value: _timestamp_from_days(current_time, float(value))
    )
    missing_matured = out["matured_at"].isna() & out["days_since_maturity"].gt(0.0)
    out.loc[missing_matured, "matured_at"] = out.loc[missing_matured, "days_since_maturity"].map(
        lambda value: _timestamp_from_days(current_time, float(value))
    )
    return out


def _apply_family_runtime_reconstruction(
    frame: pd.DataFrame,
    *,
    series: pd.Series,
    fruit_harvest_family: str,
    diagnostics: dict[str, float | int | str | bool],
) -> tuple[pd.DataFrame, dict[str, float | int | str | bool]]:
    if frame.empty or fruit_harvest_family == "tomsim_truss":
        return frame, diagnostics

    out = _prepare_runtime_clock_fields(frame, current_time=pd.Timestamp(series.get("datetime")))
    if not bool(out["proxy_state_flag"].fillna(False).astype(bool).any()) and not bool(
        diagnostics.get("synthetic_fruit_state_flag", False)
    ):
        diagnostics["proxy_mode_used"] = False
        diagnostics["family_state_mode_distribution"] = _distribution_json(
            pd.Series([str(diagnostics.get("family_state_mode", "native_payload"))])
        )
        return out, diagnostics
    runtime_signal = (
        out["days_since_anthesis"].gt(0.0)
        | out["days_since_maturity"].gt(0.0)
        | out["anthesis_at"].notna()
        | out["matured_at"].notna()
    )
    if not bool(runtime_signal.any()):
        diagnostics["proxy_mode_used"] = True
        diagnostics["family_state_mode_distribution"] = _distribution_json(pd.Series([diagnostics.get("family_state_mode", "")]))
        return out, diagnostics

    if fruit_harvest_family == "dekoning_fds":
        anthesis_progress = (out["days_since_anthesis"] / 18.0).clip(lower=0.0, upper=1.0)
        maturity_progress = (out["days_since_maturity"] / 6.0).clip(lower=0.0, upper=1.0)
        out["fds"] = (0.65 * out["tdvs"] + 0.35 * anthesis_progress + 0.20 * maturity_progress).clip(lower=0.0, upper=1.05)
        out.loc[runtime_signal, "proxy_state_flag"] = False
        diagnostics["family_state_mode"] = "dekoning_runtime_reconstruction"
        diagnostics["fds_proxy_used"] = bool((~runtime_signal).any())
    elif fruit_harvest_family == "tomgro_ageclass":
        age_progress = (out["days_since_anthesis"] / 1.6).clip(lower=1.0, upper=20.0).round()
        out["age_class"] = age_progress.where(runtime_signal, out["age_class"])
        out["mature_pool_flag"] = out["mature_pool_flag"] | out["days_since_maturity"].gt(0.0) | out["age_class"].ge(16.0)
        out["mature_pool_residence_days"] = out["days_since_maturity"].where(out["mature_pool_flag"], 0.0).clip(lower=0.0)
        out.loc[runtime_signal, "proxy_state_flag"] = False
        diagnostics["family_state_mode"] = "tomgro_mature_pool_reconstruction"
    elif fruit_harvest_family == "vanthoor_boxcar":
        stage_progress = (out["days_since_anthesis"] / 4.5).clip(lower=1.0, upper=5.0).round()
        out["stage_index"] = stage_progress.where(runtime_signal, out["stage_index"])
        out["final_stage_flag"] = out["final_stage_flag"] | out["days_since_maturity"].gt(0.0) | out["stage_index"].ge(5.0)
        out["final_stage_residence_days"] = out["days_since_maturity"].where(out["final_stage_flag"], 0.0).clip(lower=0.0)
        explicit_capacity = max(
            _float_from(series, "MCFruitHar_g_m2_d", 0.0),
            _float_from(series, "DMHar_g_m2_d", 0.0),
            _float_from(series, "fruit_harvest_g_m2_step", 0.0),
        )
        out["explicit_outflow_capacity_g_m2_d"] = _clip_series(
            out.get("explicit_outflow_capacity_g_m2_d"),
            lower=0.0,
        ).where(out.get("explicit_outflow_capacity_g_m2_d").notna(), explicit_capacity)
        if explicit_capacity > 0.0:
            out["explicit_outflow_capacity_g_m2_d"] = out["explicit_outflow_capacity_g_m2_d"].clip(lower=explicit_capacity)
        out.loc[runtime_signal, "proxy_state_flag"] = False
        diagnostics["family_state_mode"] = "vanthoor_final_stage_reconstruction"

    if fruit_harvest_family in {"dekoning_fds", "tomgro_ageclass", "vanthoor_boxcar"}:
        diagnostics["native_family_state_available"] = True
        diagnostics["synthetic_fruit_state_flag"] = bool(out["proxy_state_flag"].any())
        diagnostics["proxy_mode_used"] = bool(out["proxy_state_flag"].any())
        diagnostics["family_state_mode_distribution"] = _distribution_json(
            pd.Series(
                [
                    diagnostics["family_state_mode"] if not bool(flag) else "shared_tdvs_proxy"
                    for flag in out["proxy_state_flag"].fillna(False).astype(bool).tolist()
                ]
            )
        )
    return out, diagnostics


def _parse_truss_payload(
    series: pd.Series,
    *,
    prior_fruit_entities: pd.DataFrame,
    allow_bulk_proxy: bool,
    fruit_harvest_family: str | None = None,
) -> tuple[pd.DataFrame, dict[str, float | int | str | bool]]:
    payload = series.get("truss_cohorts_json", "")
    records: list[dict[str, object]] = []
    target_family = str(fruit_harvest_family or series.get("harvest_family_semantics", "unknown"))
    diagnostics: dict[str, float | int | str | bool] = {
        "family_state_mode": "native_payload",
        "native_family_state_available": True,
        "synthetic_fruit_state_flag": False,
        "tdvs_proxy_used": False,
    }
    if isinstance(payload, str) and payload.strip():
        try:
            parsed = json.loads(payload)
        except json.JSONDecodeError:
            parsed = []
        if isinstance(parsed, list):
            records = [record for record in parsed if isinstance(record, dict)]

    if not records:
        fruit_dm = _float_from(series, "fruit_dry_weight_g_m2", 0.0)
        if fruit_dm <= 0.0:
            diagnostics["native_family_state_available"] = False
            return pd.DataFrame(columns=FRUIT_ENTITY_COLUMNS), diagnostics
        diagnostics.update(
            {
                "family_state_mode": "shared_tdvs_proxy",
                "native_family_state_available": False,
                "synthetic_fruit_state_flag": True,
                "tdvs_proxy_used": True,
            }
        )
        semantics = target_family if target_family and target_family != "unknown" else str(series.get("harvest_family_semantics", "bulk_fruit"))
        if (not allow_bulk_proxy) and semantics not in {"tomsim_truss", "bulk_fruit"}:
            diagnostics["proxy_mode_used"] = True
        records = [
            {
                "entity_id": "fruit_bulk_001",
                "family_semantics": semantics,
                "truss_id": 1.0,
                "fruit_position": 1.0,
                "age_class": _float_from(series, "age_class", 1.0),
                "stage_index": _float_from(series, "stage_index", 1.0),
                "tdvs": _float_from(series, "mean_truss_tdvs", 0.0),
                "fds": pd.NA,
                "fruit_dm_g_m2": fruit_dm,
                "fruit_count": max(_float_from(series, "n_fruits_per_truss", 1.0), 1.0),
                "sink_active_flag": True,
                "mature_flag": False,
                "harvest_ready_flag": False,
                "onplant_flag": True,
                "harvested_flag": False,
                "days_since_anthesis": 0.0,
                "days_since_maturity": 0.0,
                "mature_pool_flag": False,
                "mature_pool_residence_days": 0.0,
                "final_stage_flag": False,
                "final_stage_residence_days": 0.0,
                "explicit_outflow_capacity_g_m2_d": 0.0,
                "proxy_state_flag": True,
                "potential_weight_proxy_g_m2": fruit_dm,
            }
        ]

    frame = pd.DataFrame(records)
    if "family_semantics" not in frame.columns:
        frame["family_semantics"] = target_family
    frame = ensure_entity_frame(frame, FRUIT_ENTITY_COLUMNS)
    frame = _merge_prior_runtime_fields(frame, prior_fruit_entities)

    tdvs_numeric = pd.to_numeric(frame.get("tdvs"), errors="coerce").fillna(0.0)
    if frame.get("fds").isna().all():
        diagnostics["tdvs_proxy_used"] = True
        frame["fds"] = tdvs_numeric
        frame["proxy_state_flag"] = True
    else:
        frame["fds"] = pd.to_numeric(frame.get("fds"), errors="coerce")
        missing_fds = frame["fds"].isna()
        if bool(missing_fds.any()):
            diagnostics["tdvs_proxy_used"] = True
            frame.loc[missing_fds, "fds"] = tdvs_numeric.loc[missing_fds]
            frame.loc[missing_fds, "proxy_state_flag"] = True

    frame["tdvs"] = tdvs_numeric
    if frame.get("age_class").isna().all():
        frame["age_class"] = tdvs_numeric.apply(lambda value: float(_int_stage_from_tdvs(value, max_stage=20)))
    if frame.get("stage_index").isna().all():
        frame["stage_index"] = tdvs_numeric.apply(lambda value: float(_int_stage_from_tdvs(value, max_stage=5)))
    frame["fruit_dm_g_m2"] = pd.to_numeric(frame.get("fruit_dm_g_m2"), errors="coerce").fillna(0.0)
    frame["fruit_count"] = pd.to_numeric(frame.get("fruit_count"), errors="coerce").fillna(0.0)
    frame["days_since_anthesis"] = pd.to_numeric(frame.get("days_since_anthesis"), errors="coerce").fillna(0.0)
    frame["days_since_maturity"] = pd.to_numeric(frame.get("days_since_maturity"), errors="coerce").fillna(0.0)
    frame["mature_pool_residence_days"] = pd.to_numeric(frame.get("mature_pool_residence_days"), errors="coerce").fillna(
        frame["days_since_maturity"]
    )
    frame["final_stage_residence_days"] = pd.to_numeric(frame.get("final_stage_residence_days"), errors="coerce").fillna(
        frame["days_since_maturity"]
    )
    frame["explicit_outflow_capacity_g_m2_d"] = pd.to_numeric(
        frame.get("explicit_outflow_capacity_g_m2_d"),
        errors="coerce",
    ).fillna(0.0)
    frame["sink_active_flag"] = frame["sink_active_flag"].map(lambda value: _bool_from(value, True))
    frame["mature_flag"] = frame["mature_flag"].map(lambda value: _bool_from(value, False))
    frame["harvest_ready_flag"] = frame["harvest_ready_flag"].map(lambda value: _bool_from(value, False))
    frame["onplant_flag"] = frame["onplant_flag"].map(lambda value: _bool_from(value, True))
    frame["harvested_flag"] = frame["harvested_flag"].map(lambda value: _bool_from(value, False))
    frame["mature_pool_flag"] = frame["mature_pool_flag"].map(lambda value: _bool_from(value, False))
    frame["final_stage_flag"] = frame["final_stage_flag"].map(lambda value: _bool_from(value, False))
    frame["proxy_state_flag"] = frame["proxy_state_flag"].map(lambda value: _bool_from(value, False))
    frame["potential_weight_proxy_g_m2"] = pd.to_numeric(
        frame.get("potential_weight_proxy_g_m2"),
        errors="coerce",
    ).fillna(frame["fruit_dm_g_m2"])
    diagnostics["synthetic_fruit_state_flag"] = bool(frame["proxy_state_flag"].any()) or bool(
        diagnostics["synthetic_fruit_state_flag"]
    )
    if diagnostics["synthetic_fruit_state_flag"]:
        diagnostics["family_state_mode"] = "shared_tdvs_proxy"
    diagnostics["native_family_state_available"] = not bool(diagnostics["synthetic_fruit_state_flag"])
    frame, diagnostics = _apply_family_runtime_reconstruction(
        frame,
        series=series,
        fruit_harvest_family=target_family,
        diagnostics=diagnostics,
    )
    frame["family_semantics"] = target_family
    diagnostics.setdefault("proxy_mode_used", bool(frame["proxy_state_flag"].fillna(False).astype(bool).any()))
    diagnostics.setdefault(
        "family_state_mode_distribution",
        _distribution_json(pd.Series([str(diagnostics.get("family_state_mode", ""))])),
    )
    return frame, diagnostics


def _synthesize_leaf_entities(series: pd.Series, fruit_entities: pd.DataFrame) -> pd.DataFrame:
    leaf_dm = _float_from(series, "leaf_dry_weight_g_m2", 0.0)
    lai = _float_from(series, "LAI", 0.0)
    if leaf_dm <= 0.0 and lai <= 0.0:
        return pd.DataFrame(columns=LEAF_ENTITY_COLUMNS)
    truss_ids = sorted(
        {
            int(float(value))
            for value in pd.to_numeric(fruit_entities.get("truss_id"), errors="coerce").dropna().tolist()
            if float(value) >= 1.0
        }
    )
    if not truss_ids:
        fallback = max(int(round(_float_from(series, "truss_count", 1.0))), 1)
        truss_ids = list(range(1, fallback + 1))
    per_leaf_dm = leaf_dm / len(truss_ids) if truss_ids else 0.0
    per_leaf_area = lai / len(truss_ids) if truss_ids else 0.0
    tdvs_by_truss = {}
    if not fruit_entities.empty:
        grouped = fruit_entities.groupby("truss_id")["tdvs"].max()
        tdvs_by_truss = {int(float(key)): float(value) for key, value in grouped.items()}
    records = [
        {
            "entity_id": f"leaf_unit_{truss_id:03d}",
            "linked_truss_id": float(truss_id),
            "vpos": float(truss_id),
            "vds": tdvs_by_truss.get(truss_id, _float_from(series, "mean_truss_tdvs", 0.0)),
            "leaf_dm_g_m2": per_leaf_dm,
            "leaf_area_m2_m2": per_leaf_area,
            "onplant_flag": True,
            "harvested_flag": False,
        }
        for truss_id in truss_ids
    ]
    return ensure_entity_frame(pd.DataFrame(records), LEAF_ENTITY_COLUMNS)


def normalize_harvest_state(
    current_row: pd.Series | Mapping[str, object],
    prior_row: pd.Series | Mapping[str, object] | None = None,
    *,
    plants_per_m2: float = 1.836091,
    floor_area_basis: bool = True,
    allow_bulk_proxy: bool = True,
    fruit_harvest_family: str | None = None,
) -> HarvestState:
    current = _as_series(current_row)
    prior = _as_series(prior_row)
    current_time = pd.Timestamp(current.get("datetime"))
    if prior is not None and pd.notna(prior.get("datetime")):
        dt_days = max((current_time - pd.Timestamp(prior.get("datetime"))).total_seconds() / 86400.0, 0.0)
    else:
        dt_days = max(_float_from(current, "dt_days", 1.0), 1e-9)
    prior_fruit_entities = _prior_fruit_lookup(prior)
    fruit_entities, fruit_diagnostics = _parse_truss_payload(
        current,
        prior_fruit_entities=prior_fruit_entities,
        allow_bulk_proxy=allow_bulk_proxy,
        fruit_harvest_family=fruit_harvest_family,
    )
    leaf_entities = _synthesize_leaf_entities(current, fruit_entities)
    stem_root_state = {
        "stem_dry_weight_g_m2": _float_from(current, "stem_dry_weight_g_m2", 0.0),
        "root_dry_weight_g_m2": _float_from(current, "root_dry_weight_g_m2", 0.0),
        "reserve_pool_g_m2": _float_from(current, "reserve_pool_g_m2", 0.0),
        "buffer_pool_g_m2": _float_from(current, "buffer_pool_g_m2", 0.0),
    }
    diagnostics: dict[str, float | int | str | bool] = {
        "truss_count": _float_from(current, "truss_count", float(len(fruit_entities))),
        "active_trusses": _float_from(current, "active_trusses", float(len(fruit_entities))),
        "fruit_harvest_g_m2_step": _float_from(current, "fruit_harvest_g_m2_step", 0.0),
        "leaf_harvest_g_m2_step": _float_from(current, "leaf_harvest_g_m2_step", 0.0),
        **fruit_diagnostics,
    }
    return HarvestState(
        datetime=current_time,
        dt_days=dt_days,
        floor_area_basis=bool(floor_area_basis),
        plants_per_m2=float(plants_per_m2),
        lai=_float_from(current, "LAI", 0.0),
        cbuf_g_m2=_float_from(current, "buffer_pool_g_m2", 0.0),
        fruit_entities=fruit_entities,
        leaf_entities=leaf_entities,
        stem_root_state=stem_root_state,
        harvested_fruit_cumulative_g_m2=_float_from(current, "harvested_fruit_g_m2", 0.0),
        harvested_leaf_cumulative_g_m2=_float_from(current, "harvested_leaf_g_m2", 0.0),
        diagnostics=diagnostics,
    )


def snapshot_to_harvest_state(
    current_row: pd.Series | Mapping[str, object],
    prior_row: pd.Series | Mapping[str, object] | None = None,
    *,
    plants_per_m2: float = 1.836091,
    floor_area_basis: bool = True,
    allow_bulk_proxy: bool = True,
    fruit_harvest_family: str | None = None,
) -> HarvestState:
    return normalize_harvest_state(
        current_row,
        prior_row=prior_row,
        plants_per_m2=plants_per_m2,
        floor_area_basis=floor_area_basis,
        allow_bulk_proxy=allow_bulk_proxy,
        fruit_harvest_family=fruit_harvest_family,
    )


__all__ = ["normalize_harvest_state", "snapshot_to_harvest_state"]
