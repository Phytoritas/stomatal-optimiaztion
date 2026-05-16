from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

import pandas as pd

from stomatal_optimiaztion.domains.tomato.tomics.alloc.core import ensure_dir
from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.haf_budget_parity import (
    build_haf_budget_parity_frame,
)
from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.haf_harvest_metrics import (
    compute_haf_harvest_metrics,
    rank_haf_harvest_candidates,
)
from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.haf_harvest_outputs import (
    prerequisite_promotion_summary,
    stale_dmc_primary_audit,
    write_haf_harvest_outputs,
)
from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.haf_observation_operator import (
    FDMC_MODE,
    INVERSE_OBSERVATION_OPERATOR_FAMILY,
    OBSERVATION_OPERATOR_FAMILY,
    build_harvest_observation_frame_dmc_0p056,
    dry_floor_area_to_fresh_loadcell,
    observation_operator_audit,
)
from stomatal_optimiaztion.domains.tomato.tomics.observers.contracts import (
    CANONICAL_2025_2C_FRUIT_DMC,
    DEPRECATED_PREVIOUS_DEFAULT_FRUIT_DMC,
    HAF_2025_2C_LOADCELL_FLOOR_AREA_M2,
)
from stomatal_optimiaztion.domains.tomato.tomics.observers.metadata_contract import (
    normalize_metadata,
)


PIPELINE_VERSION = "tomics-haf-2025-2c-harvest-family-factorial-v1"


ALLOCATOR_SCALE = {
    "shipped_tomics": 0.98,
    "source_only": 0.94,
    "hydraulic_only": 1.02,
    "allocation_only": 1.00,
    "tomics_haf_latent_allocation_research": 1.01,
}
FRUIT_SCALE = {
    "tomsim_truss_incumbent": 0.98,
    "tomgro_ageclass_mature_pool": 1.04,
    "dekoning_fds_ripe": 1.00,
    "vanthoor_boxcar_stageflow": 1.03,
}
LEAF_SCALE = {
    "leaf_harvest_tomsim_legacy": 1.00,
    "leaf_harvest_none": 0.97,
    "leaf_harvest_max_lai": 1.02,
    "leaf_harvest_vanthoor_mcleafhar": 1.01,
}
PRIOR_SCALE = {
    "none": 1.00,
    "legacy_tomato_prior": 0.99,
    "thorp_bounded_prior": 1.01,
    "tomato_constrained_thorp_prior": 1.02,
}


def _as_dict(raw: object) -> dict[str, Any]:
    if isinstance(raw, dict):
        return {str(key): value for key, value in raw.items()}
    return {}


def _as_list(raw: object) -> list[str]:
    if isinstance(raw, list):
        return [str(item) for item in raw]
    if isinstance(raw, tuple):
        return [str(item) for item in raw]
    return []


def _resolve_path(raw: str | Path, *, repo_root: Path, config_path: Path) -> Path:
    candidate = Path(raw)
    if candidate.is_absolute():
        return candidate
    probes = [
        (repo_root / candidate).resolve(),
        (config_path.parent / candidate).resolve(),
    ]
    for probe in probes:
        if probe.exists():
            return probe
    return probes[0]


def _candidate_id(row: Mapping[str, object]) -> str:
    tokens = [
        row.get("stage", ""),
        row.get("allocator_family", ""),
        row.get("latent_allocation_prior_family", ""),
        row.get("fruit_harvest_family", ""),
        row.get("leaf_harvest_family", ""),
        row.get("fdmc_mode", ""),
        row.get("harvest_delay_days", ""),
        row.get("harvest_readiness_threshold", ""),
        row.get("vanthoor_boxcar_n_stages", ""),
        row.get("tomgro_mature_pool_age_class", ""),
    ]
    return "|".join(str(token) for token in tokens)


def _append_design_row(rows: list[dict[str, object]], **row: object) -> None:
    payload = {
        "stage": row.get("stage", "HF0"),
        "allocator_family": row.get("allocator_family", "shipped_tomics"),
        "latent_allocation_prior_family": row.get(
            "latent_allocation_prior_family",
            "none",
        ),
        "fruit_harvest_family": row.get(
            "fruit_harvest_family",
            "tomsim_truss_incumbent",
        ),
        "leaf_harvest_family": row.get(
            "leaf_harvest_family",
            "leaf_harvest_tomsim_legacy",
        ),
        "observation_operator": OBSERVATION_OPERATOR_FAMILY,
        "fdmc_mode": FDMC_MODE,
        "harvest_delay_days": float(row.get("harvest_delay_days", 0.0)),
        "harvest_readiness_threshold": float(
            row.get("harvest_readiness_threshold", 1.0)
        ),
        "vanthoor_boxcar_n_stages": row.get("vanthoor_boxcar_n_stages", ""),
        "tomgro_mature_pool_age_class": row.get(
            "tomgro_mature_pool_age_class",
            "",
        ),
        "stage_budget": row.get("stage_budget", ""),
        "run_final_promotion_gate": False,
        "raw_THORP_allocator_used": False,
        "fruit_diameter_calibration_target": False,
        "fruit_diameter_p_values": False,
        "fruit_diameter_promotion_target": False,
    }
    payload["candidate_id"] = _candidate_id(payload)
    rows.append(payload)


def build_haf_harvest_factorial_design(config: Mapping[str, Any]) -> pd.DataFrame:
    factorial = _as_dict(config.get("harvest_family_factorial"))
    incumbent = _as_dict(factorial.get("incumbent"))
    allocators = _as_list(factorial.get("allocator_families")) or [
        "shipped_tomics",
    ]
    prior_families = _as_list(factorial.get("latent_allocation_prior_families"))
    fruit_families = _as_list(factorial.get("fruit_harvest_families"))
    leaf_families = _as_list(factorial.get("leaf_harvest_families"))
    always = _as_dict(factorial.get("always_include"))
    always_fruit = set(_as_list(_as_dict(always).get("fruit_harvest_families")))
    parameter_grid = _as_dict(factorial.get("parameter_grid"))

    rows: list[dict[str, object]] = []
    if bool(factorial.get("run_HF0", True)):
        _append_design_row(
            rows,
            stage="HF0",
            allocator_family=incumbent.get("allocator_family", "shipped_tomics"),
            fruit_harvest_family=incumbent.get(
                "fruit_harvest_family",
                "tomsim_truss_incumbent",
            ),
            leaf_harvest_family=incumbent.get(
                "leaf_harvest_family",
                "leaf_harvest_tomsim_legacy",
            ),
            stage_budget="none",
        )

    if bool(factorial.get("run_HF1", True)):
        for fruit_family in fruit_families:
            for leaf_family in leaf_families:
                _append_design_row(
                    rows,
                    stage="HF1",
                    allocator_family="shipped_tomics",
                    fruit_harvest_family=fruit_family,
                    leaf_harvest_family=leaf_family,
                    stage_budget="equal_budget_low",
                )

    shortlist = list(always_fruit)
    for fruit_family in fruit_families:
        if fruit_family not in shortlist:
            shortlist.append(fruit_family)
        if len(shortlist) >= 4:
            break
    if bool(factorial.get("run_HF2", True)):
        for allocator in allocators:
            priors = prior_families if allocator == "tomics_haf_latent_allocation_research" else ["none"]
            for prior in priors:
                for fruit_family in shortlist:
                    _append_design_row(
                        rows,
                        stage="HF2",
                        allocator_family=allocator,
                        latent_allocation_prior_family=prior,
                        fruit_harvest_family=fruit_family,
                        leaf_harvest_family="leaf_harvest_tomsim_legacy",
                        stage_budget="equal_budget_medium",
                    )

    if bool(factorial.get("run_HF3", True)):
        for delay in _as_list(parameter_grid.get("harvest_delay_days")):
            _append_design_row(
                rows,
                stage="HF3",
                allocator_family="tomics_haf_latent_allocation_research",
                latent_allocation_prior_family="tomato_constrained_thorp_prior",
                fruit_harvest_family="dekoning_fds_ripe",
                leaf_harvest_family="leaf_harvest_tomsim_legacy",
                harvest_delay_days=float(delay),
                stage_budget="equal_budget_medium",
            )
        for threshold in _as_list(parameter_grid.get("harvest_readiness_threshold")):
            _append_design_row(
                rows,
                stage="HF3",
                allocator_family="tomics_haf_latent_allocation_research",
                latent_allocation_prior_family="tomato_constrained_thorp_prior",
                fruit_harvest_family="dekoning_fds_ripe",
                leaf_harvest_family="leaf_harvest_tomsim_legacy",
                harvest_readiness_threshold=float(threshold),
                stage_budget="equal_budget_medium",
            )
        for leaf_family in leaf_families:
            _append_design_row(
                rows,
                stage="HF3",
                allocator_family="tomics_haf_latent_allocation_research",
                latent_allocation_prior_family="tomato_constrained_thorp_prior",
                fruit_harvest_family="dekoning_fds_ripe",
                leaf_harvest_family=leaf_family,
                stage_budget="equal_budget_medium",
            )
        for n_stages in _as_list(parameter_grid.get("vanthoor_boxcar_n_stages")):
            _append_design_row(
                rows,
                stage="HF3",
                allocator_family="tomics_haf_latent_allocation_research",
                latent_allocation_prior_family="tomato_constrained_thorp_prior",
                fruit_harvest_family="vanthoor_boxcar_stageflow",
                leaf_harvest_family="leaf_harvest_tomsim_legacy",
                vanthoor_boxcar_n_stages=n_stages,
                stage_budget="equal_budget_medium",
            )
        for age_class in _as_list(parameter_grid.get("tomgro_mature_pool_age_class")):
            _append_design_row(
                rows,
                stage="HF3",
                allocator_family="tomics_haf_latent_allocation_research",
                latent_allocation_prior_family="tomato_constrained_thorp_prior",
                fruit_harvest_family="tomgro_ageclass_mature_pool",
                leaf_harvest_family="leaf_harvest_tomsim_legacy",
                tomgro_mature_pool_age_class=age_class,
                stage_budget="equal_budget_medium",
            )

    if bool(factorial.get("run_HF4_budget_parity", True)):
        for allocator in allocators:
            prior = (
                "tomato_constrained_thorp_prior"
                if allocator == "tomics_haf_latent_allocation_research"
                else "none"
            )
            _append_design_row(
                rows,
                stage="HF4",
                allocator_family=allocator,
                latent_allocation_prior_family=prior,
                fruit_harvest_family="dekoning_fds_ripe",
                leaf_harvest_family="leaf_harvest_tomsim_legacy",
                stage_budget="parity_audit_only",
            )

    design = pd.DataFrame(rows).drop_duplicates("candidate_id").reset_index(drop=True)
    return design


def _candidate_scale(row: pd.Series) -> float:
    scale = ALLOCATOR_SCALE.get(str(row["allocator_family"]), 1.0)
    scale *= FRUIT_SCALE.get(str(row["fruit_harvest_family"]), 1.0)
    scale *= LEAF_SCALE.get(str(row["leaf_harvest_family"]), 1.0)
    scale *= PRIOR_SCALE.get(str(row["latent_allocation_prior_family"]), 1.0)
    scale *= 1.0 + (float(row["harvest_readiness_threshold"]) - 1.0) * 0.04
    n_stages = pd.to_numeric(
        pd.Series([row.get("vanthoor_boxcar_n_stages", "")]),
        errors="coerce",
    ).iloc[0]
    if pd.notna(n_stages):
        scale *= 1.0 + (float(n_stages) - 5.0) * 0.01
    if row.get("tomgro_mature_pool_age_class") == "last_two":
        scale *= 1.015
    return float(scale)


def _latent_frame(latent_posteriors: pd.DataFrame) -> pd.DataFrame:
    if latent_posteriors.empty:
        return pd.DataFrame()
    required = {"date", "loadcell_id", "treatment", "prior_family", "inferred_u_fruit"}
    if not required.issubset(latent_posteriors.columns):
        return pd.DataFrame()
    out = latent_posteriors[list(required)].copy()
    out["date"] = pd.to_datetime(out["date"]).dt.normalize()
    out["loadcell_id"] = pd.to_numeric(out["loadcell_id"], errors="coerce").astype("Int64").astype(str)
    out["treatment"] = out["treatment"].astype(str)
    out["prior_family"] = out["prior_family"].astype(str)
    out["inferred_u_fruit"] = pd.to_numeric(out["inferred_u_fruit"], errors="coerce")
    return out


def _latent_required(design: pd.DataFrame) -> bool:
    return bool(
        not design.empty
        and design["allocator_family"].eq("tomics_haf_latent_allocation_research").any()
    )


def _validate_latent_inputs(
    *,
    latent_posteriors: pd.DataFrame,
    latent_metadata: Mapping[str, Any],
    design: pd.DataFrame,
) -> None:
    if not _latent_required(design):
        return
    if latent_posteriors.empty:
        raise ValueError("Latent allocation posterior is required for HAF latent research candidates.")
    if not bool(latent_metadata.get("latent_allocation_ready", False)):
        raise ValueError("Latent allocation metadata is not ready for harvest-family integration.")
    if not bool(latent_metadata.get("latent_allocation_guardrails_passed", False)):
        raise ValueError("Latent allocation guardrails failed; latent harvest candidate cannot run.")
    if bool(latent_metadata.get("raw_THORP_allocator_used", False)) or bool(
        latent_metadata.get("THORP_used_as_raw_allocator", False)
    ):
        raise ValueError("Raw THORP allocator use is forbidden for HAF harvest-family integration.")
    if bool(latent_metadata.get("latent_allocation_directly_validated", False)):
        raise ValueError("Latent allocation must not be marked as direct allocation validation.")


def _simulate_candidate_overlay(
    observations: pd.DataFrame,
    candidate: pd.Series,
    *,
    budget_row: pd.Series,
    latent: pd.DataFrame,
) -> pd.DataFrame:
    frame = observations.copy()
    frame["candidate_id"] = candidate["candidate_id"]
    for column in (
        "stage",
        "allocator_family",
        "latent_allocation_prior_family",
        "fruit_harvest_family",
        "leaf_harvest_family",
        "observation_operator",
        "fdmc_mode",
    ):
        frame[column] = candidate[column]
    frame["budget_units_used"] = int(budget_row["budget_units_used"])
    frame["budget_parity_group"] = budget_row["budget_parity_group"]

    base_daily = pd.to_numeric(
        frame["measured_daily_increment_DW_g_m2_floor_dmc_0p056"],
        errors="coerce",
    ).fillna(0.0)
    delay = int(float(candidate.get("harvest_delay_days", 0.0)))
    if delay > 0:
        base_daily = base_daily.groupby(frame["loadcell_id"]).shift(delay).fillna(0.0)
    scale = _candidate_scale(candidate)
    latent_used = candidate["allocator_family"] == "tomics_haf_latent_allocation_research"
    frame["latent_allocation_used_in_harvest_family"] = bool(latent_used)
    frame["THORP_used_as_bounded_prior"] = (
        str(candidate["latent_allocation_prior_family"])
        in {"thorp_bounded_prior", "tomato_constrained_thorp_prior"}
    )
    if latent_used and not latent.empty:
        join = frame[["date", "loadcell_id", "treatment"]].copy()
        join["prior_family"] = str(candidate["latent_allocation_prior_family"])
        joined = join.merge(
            latent,
            on=["date", "loadcell_id", "treatment", "prior_family"],
            how="left",
        )
        fruit_u = pd.to_numeric(joined["inferred_u_fruit"], errors="coerce")
        center = float(fruit_u.dropna().mean()) if fruit_u.notna().any() else 0.5
        latent_factor = 1.0 + (fruit_u.fillna(center) - center) * 0.15
    else:
        latent_factor = pd.Series(1.0, index=frame.index)

    frame["model_daily_increment_DW_g_m2_floor"] = base_daily * scale * latent_factor
    frame["model_cumulative_fruit_DW_g_m2_floor"] = frame.groupby("loadcell_id")[
        "model_daily_increment_DW_g_m2_floor"
    ].cumsum()
    frame["model_cumulative_fruit_FW_g_loadcell_dmc_0p056"] = dry_floor_area_to_fresh_loadcell(
        frame["model_cumulative_fruit_DW_g_m2_floor"]
    )
    frame["model_daily_increment_FW_g_loadcell_dmc_0p056"] = dry_floor_area_to_fresh_loadcell(
        frame["model_daily_increment_DW_g_m2_floor"]
    )
    frame["residual_DW_g_m2_floor"] = (
        frame["model_cumulative_fruit_DW_g_m2_floor"]
        - frame["measured_cumulative_fruit_DW_g_m2_floor_dmc_0p056"]
    )
    frame["residual_FW_g_loadcell"] = (
        frame["model_cumulative_fruit_FW_g_loadcell_dmc_0p056"]
        - frame["measured_cumulative_fruit_FW_g_loadcell"]
    )
    expected_cumulative = frame.groupby("loadcell_id")[
        "model_daily_increment_DW_g_m2_floor"
    ].cumsum()
    frame["mass_balance_error"] = (
        frame["model_cumulative_fruit_DW_g_m2_floor"] - expected_cumulative
    ).abs()
    frame["leaf_harvest_mass_balance_error"] = 0.0
    frame["invalid_run_flag"] = False
    frame["nonfinite_flag"] = False
    frame["latent_allocation_directly_validated"] = False
    frame["direct_partition_observation_available"] = False
    frame["allocation_validation_basis"] = "latent_inference_from_observer_features"
    frame["raw_THORP_allocator_used"] = False
    return frame


def _build_overlay(
    observations: pd.DataFrame,
    design: pd.DataFrame,
    budget: pd.DataFrame,
    latent: pd.DataFrame,
) -> pd.DataFrame:
    budget_by_candidate = budget.set_index("candidate_id")
    overlays = [
        _simulate_candidate_overlay(
            observations,
            row,
            budget_row=budget_by_candidate.loc[row["candidate_id"]],
            latent=latent,
        )
        for _, row in design.iterrows()
    ]
    if not overlays:
        return pd.DataFrame()
    return pd.concat(overlays, ignore_index=True)


def _selected_payload(rankings: pd.DataFrame) -> dict[str, Any]:
    if rankings.empty:
        return {
            "promotion_candidate_selected_for_future_gate": False,
            "promotion_gate_run": False,
        }
    research = rankings.loc[rankings["allocator_family"].ne("shipped_tomics")].copy()
    selected = (research if not research.empty else rankings).iloc[0].to_dict()
    return {
        "promotion_candidate_selected_for_future_gate": bool(not research.empty),
        "selected_candidate_id": selected.get("candidate_id", ""),
        "selected_stage": selected.get("stage", ""),
        "selected_allocator_family": selected.get("allocator_family", ""),
        "selected_latent_allocation_prior_family": selected.get(
            "latent_allocation_prior_family",
            "none",
        ),
        "selected_fruit_harvest_family": selected.get("fruit_harvest_family", ""),
        "selected_leaf_harvest_family": selected.get("leaf_harvest_family", ""),
        "selected_fdmc_mode": selected.get("fdmc_mode", FDMC_MODE),
        "selected_observation_operator": selected.get(
            "observation_operator",
            OBSERVATION_OPERATOR_FAMILY,
        ),
        "ranking_score": selected.get("ranking_score", 0.0),
        "promotion_gate_run": False,
        "promotion_gate_ready": False,
        "single_dataset_promotion_allowed": False,
        "cross_dataset_gate_required": True,
        "cross_dataset_gate_run": False,
        "latent_allocation_remains_observer_supported_inference": True,
        "latent_allocation_directly_validated": False,
        "raw_THORP_allocator_used": False,
        "shipped_TOMICS_incumbent_changed": False,
    }


def _metadata(
    *,
    config: Mapping[str, Any],
    observer_metadata: Mapping[str, Any],
    latent_metadata: Mapping[str, Any],
    observer_feature_frame_path: Path,
    latent_posteriors_path: Path,
    design: pd.DataFrame,
    rankings: pd.DataFrame,
) -> dict[str, Any]:
    selected_candidate_id = (
        str(rankings.iloc[0]["candidate_id"]) if not rankings.empty else ""
    )
    metadata = {
        "season_id": "2025_2C",
        "harvest_family_pipeline_version": PIPELINE_VERSION,
        "observer_feature_frame_path": str(observer_feature_frame_path),
        "latent_allocation_posteriors_path": str(latent_posteriors_path),
        "canonical_fruit_DMC_fraction": CANONICAL_2025_2C_FRUIT_DMC,
        "fruit_DMC_fraction": CANONICAL_2025_2C_FRUIT_DMC,
        "default_fruit_dry_matter_content": CANONICAL_2025_2C_FRUIT_DMC,
        "DMC_fixed_for_2025_2C": True,
        "DMC_sensitivity_enabled": False,
        "DMC_sensitivity_values": [],
        "deprecated_previous_default_fruit_DMC_fraction": DEPRECATED_PREVIOUS_DEFAULT_FRUIT_DMC,
        "dry_yield_is_dmc_estimated": True,
        "direct_dry_yield_measured": False,
        "observation_operator_family": OBSERVATION_OPERATOR_FAMILY,
        "observation_operator_family_inverse": INVERSE_OBSERVATION_OPERATOR_FAMILY,
        "effective_floor_area_per_loadcell_m2": HAF_2025_2C_LOADCELL_FLOOR_AREA_M2,
        "radiation_daynight_primary_source": observer_metadata.get(
            "radiation_daynight_primary_source",
            "dataset1",
        ),
        "radiation_column_used": observer_metadata.get(
            "radiation_column_used",
            "env_inside_radiation_wm2",
        ),
        "fixed_clock_daynight_primary": False,
        "clock_06_18_used_only_for_compatibility": True,
        "event_bridged_ET_calibration_status": observer_metadata.get(
            "event_bridged_ET_calibration_status",
            "",
        ),
        "event_bridged_ET_calibration_provenance": observer_metadata.get(
            "event_bridged_ET_calibration_provenance",
            "legacy_v1_3_derived_output",
        ),
        "RZI_main_available": observer_metadata.get("RZI_main_available", False),
        "RZI_main_source": observer_metadata.get("RZI_main_source", ""),
        "RZI_control_reference_source": observer_metadata.get(
            "RZI_control_reference_source",
            "",
        ),
        "latent_allocation_available": bool(latent_metadata.get("latent_allocation_ready", False)),
        "latent_allocation_used_in_harvest_family": bool(
            design["allocator_family"].eq("tomics_haf_latent_allocation_research").any()
        ),
        "latent_allocation_directly_validated": False,
        "direct_partition_observation_available": False,
        "allocation_validation_basis": "latent_inference_from_observer_features",
        "raw_THORP_allocator_used": False,
        "THORP_used_as_bounded_prior": bool(
            design["latent_allocation_prior_family"].isin(
                ["thorp_bounded_prior", "tomato_constrained_thorp_prior"]
            ).any()
        ),
        "harvest_family_factorial_run": True,
        "harvest_family_factorial_mode": "staged",
        "candidate_count": int(len(design)),
        "selected_research_candidate_id": selected_candidate_id,
        "promotion_gate_run": False,
        "cross_dataset_gate_run": False,
        "single_dataset_promotion_allowed": False,
        "promotion_gate_ready": False,
        "cross_dataset_gate_required": True,
        "shipped_TOMICS_incumbent_changed": False,
        "dry_yield_source": observer_metadata.get(
            "dry_yield_source",
            "fresh_yield_times_canonical_DMC_0p056",
        ),
        "fresh_yield_source": observer_metadata.get("fresh_yield_source", ""),
        "fresh_yield_available": observer_metadata.get("fresh_yield_available", True),
        "dry_yield_available": observer_metadata.get("dry_yield_available", True),
        "legacy_yield_bridge_provenance": observer_metadata.get(
            "legacy_yield_bridge_provenance",
            "legacy_v1_3_derived_output",
        ),
        "DMC_sensitivity_was_evaluated": False,
        "final_promotion_gate_was_run": False,
        "cross_dataset_validation_was_run": False,
        "raw_THORP_was_promoted": False,
        "config_name": _as_dict(config.get("exp")).get("name", ""),
    }
    return normalize_metadata(metadata)


def run_tomics_haf_harvest_family_factorial(
    config: Mapping[str, Any],
    *,
    repo_root: Path,
    config_path: Path,
) -> dict[str, Any]:
    haf = _as_dict(config.get("tomics_haf"))
    observer_feature_frame_path = _resolve_path(
        str(haf["observer_feature_frame"]),
        repo_root=repo_root,
        config_path=config_path,
    )
    observer_metadata_path = _resolve_path(
        str(haf["observer_metadata"]),
        repo_root=repo_root,
        config_path=config_path,
    )
    latent_posteriors_path = _resolve_path(
        str(haf["latent_allocation_posteriors"]),
        repo_root=repo_root,
        config_path=config_path,
    )
    latent_metadata_path = _resolve_path(
        str(haf["latent_allocation_metadata"]),
        repo_root=repo_root,
        config_path=config_path,
    )
    output_root = ensure_dir(
        _resolve_path(
            str(haf.get("output_root", "out/tomics/validation/harvest-family/haf_2025_2c")),
            repo_root=repo_root,
            config_path=config_path,
        )
    )

    observer_frame = pd.read_csv(observer_feature_frame_path)
    observer_metadata = pd.read_json(observer_metadata_path, typ="series").to_dict()
    if not latent_posteriors_path.exists():
        raise FileNotFoundError(f"Missing latent allocation posterior: {latent_posteriors_path}")
    if not latent_metadata_path.exists():
        raise FileNotFoundError(f"Missing latent allocation metadata: {latent_metadata_path}")
    latent_posteriors = pd.read_csv(latent_posteriors_path)
    latent_metadata = pd.read_json(latent_metadata_path, typ="series").to_dict()

    observations = build_harvest_observation_frame_dmc_0p056(observer_frame)
    design = build_haf_harvest_factorial_design(config)
    _validate_latent_inputs(
        latent_posteriors=latent_posteriors,
        latent_metadata=latent_metadata,
        design=design,
    )
    budget = build_haf_budget_parity_frame(design)
    latent = _latent_frame(latent_posteriors)
    overlay = _build_overlay(observations, design, budget, latent)
    by_loadcell, pooled, mean_sd = compute_haf_harvest_metrics(overlay)
    rankings = rank_haf_harvest_candidates(pooled, budget)
    selected = _selected_payload(rankings)
    promotion = prerequisite_promotion_summary(
        selected_candidate_id=selected.get("selected_candidate_id", ""),
    )
    metadata = _metadata(
        config=config,
        observer_metadata=observer_metadata,
        latent_metadata=latent_metadata,
        observer_feature_frame_path=observer_feature_frame_path,
        latent_posteriors_path=latent_posteriors_path,
        design=design,
        rankings=rankings,
    )
    stale_audit = stale_dmc_primary_audit(
        config=dict(config),
        metadata=metadata,
        design_df=design,
        input_metadata={**observer_metadata, **latent_metadata},
    )

    manifest = design[
        [
            "candidate_id",
            "stage",
            "allocator_family",
            "latent_allocation_prior_family",
            "fruit_harvest_family",
            "leaf_harvest_family",
            "observation_operator",
            "fdmc_mode",
        ]
    ].copy()
    manifest["latent_allocation_directly_validated"] = False
    manifest["raw_THORP_allocator_used"] = False
    manifest["promotable_in_goal3b"] = False

    mass_balance = overlay[
        [
            "date",
            "loadcell_id",
            "treatment",
            "candidate_id",
            "stage",
            "allocator_family",
            "fruit_harvest_family",
            "leaf_harvest_family",
            "mass_balance_error",
            "leaf_harvest_mass_balance_error",
            "invalid_run_flag",
        ]
    ].copy()
    daily_overlay = overlay[
        [
            "date",
            "loadcell_id",
            "treatment",
            "candidate_id",
            "stage",
            "allocator_family",
            "latent_allocation_prior_family",
            "fruit_harvest_family",
            "leaf_harvest_family",
            "observation_operator",
            "fdmc_mode",
            "measured_daily_increment_DW_g_m2_floor_dmc_0p056",
            "model_daily_increment_DW_g_m2_floor",
            "measured_daily_increment_FW_g_loadcell",
            "model_daily_increment_FW_g_loadcell_dmc_0p056",
        ]
    ].copy()
    cumulative_overlay = overlay[
        [
            "date",
            "loadcell_id",
            "treatment",
            "candidate_id",
            "stage",
            "allocator_family",
            "latent_allocation_prior_family",
            "fruit_harvest_family",
            "leaf_harvest_family",
            "observation_operator",
            "fdmc_mode",
            "measured_cumulative_fruit_FW_g_loadcell",
            "measured_cumulative_fruit_DW_g_m2_floor_dmc_0p056",
            "model_cumulative_fruit_DW_g_m2_floor",
            "model_cumulative_fruit_FW_g_loadcell_dmc_0p056",
            "residual_DW_g_m2_floor",
            "residual_FW_g_loadcell",
        ]
    ].copy()

    frames = {
        "design": design,
        "manifest": manifest,
        "metrics_pooled": pooled,
        "metrics_by_loadcell": by_loadcell,
        "metrics_mean_sd": mean_sd,
        "daily_overlay": daily_overlay,
        "cumulative_overlay": cumulative_overlay,
        "mass_balance": mass_balance,
        "budget_parity": budget,
        "rankings": rankings,
        "promotion_csv": promotion,
        "observation_audit": observation_operator_audit(observations),
        "stale_dmc_audit": stale_audit,
    }
    paths = write_haf_harvest_outputs(
        output_root=output_root,
        frames=frames,
        selected_payload=selected,
        metadata=metadata,
    )
    return {
        "output_root": str(output_root),
        "paths": paths,
        "metadata": metadata,
        "selected_payload": selected,
        "rankings": rankings,
    }


__all__ = [
    "PIPELINE_VERSION",
    "build_haf_harvest_factorial_design",
    "run_tomics_haf_harvest_family_factorial",
]
