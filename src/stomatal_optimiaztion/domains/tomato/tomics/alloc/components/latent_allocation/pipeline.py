from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

from stomatal_optimiaztion.domains.tomato.tomics.alloc.components.latent_allocation.contracts import (
    DIRECT_VALIDATION_STATEMENT,
    LATENT_ALLOCATION_PIPELINE_VERSION,
    OUTPUT_FILENAMES,
    PRIOR_FAMILIES,
    SEASON_ID,
    as_dict,
    resolve_repo_path,
)
from stomatal_optimiaztion.domains.tomato.tomics.alloc.components.latent_allocation.diagnostics import (
    compute_allocation_identifiability,
    compute_observer_support_scores,
    compute_prior_family_diagnostics,
)
from stomatal_optimiaztion.domains.tomato.tomics.alloc.components.latent_allocation.guardrails import (
    evaluate_latent_allocation_guardrails,
)
from stomatal_optimiaztion.domains.tomato.tomics.alloc.components.latent_allocation.inference import (
    infer_latent_allocation,
)
from stomatal_optimiaztion.domains.tomato.tomics.alloc.components.latent_allocation.input_state import (
    build_latent_allocation_input_state,
    check_production_preconditions,
)
from stomatal_optimiaztion.domains.tomato.tomics.alloc.components.latent_allocation.priors import (
    build_latent_allocation_priors,
)
from stomatal_optimiaztion.domains.tomato.tomics.alloc.core import ensure_dir, load_config, write_json


def _repo_root_from_config(config_path: Path, config: dict[str, Any]) -> Path:
    repo_root_value = config.get("paths", {}).get("repo_root", "../..")
    repo_root = Path(repo_root_value)
    if repo_root.is_absolute():
        return repo_root.resolve()
    return (config_path.parent / repo_root).resolve()


def _tomics_haf_config(config: dict[str, Any]) -> dict[str, Any]:
    return as_dict(config.get("tomics_haf"))


def _write_csv(output_root: Path, key: str, frame: pd.DataFrame) -> Path:
    ensure_dir(output_root)
    path = output_root / OUTPUT_FILENAMES[key]
    frame.to_csv(path, index=False, encoding="utf-8")
    return path


def _write_text(output_root: Path, key: str, text: str) -> Path:
    ensure_dir(output_root)
    path = output_root / OUTPUT_FILENAMES[key]
    path.write_text(text, encoding="utf-8")
    return path


def _read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        loaded = json.load(handle)
    return loaded if isinstance(loaded, dict) else {}


def _guardrail_pass_map(guardrails: pd.DataFrame) -> dict[str, bool]:
    if guardrails.empty:
        return {}
    return {
        f"{str(row['guardrail_name'])}_guard_passed": bool(row["pass_fail"])
        for _, row in guardrails.iterrows()
    }


def _truthy(value: object) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        return value.strip().lower() in {"true", "1", "yes", "y"}
    return False


def _frame_flag_any(frame: pd.DataFrame, column: str) -> bool:
    if column not in frame.columns:
        return False
    return bool(frame[column].fillna(False).map(_truthy).any())


def _forbidden_contract_metadata(
    observer_metadata: dict[str, Any],
    feature_frame: pd.DataFrame,
) -> dict[str, Any]:
    return {
        "raw_THORP_allocator_used": bool(observer_metadata.get("raw_THORP_allocator_used", False))
        or _frame_flag_any(feature_frame, "raw_THORP_allocator_used"),
        "fruit_diameter_p_values_allowed": bool(observer_metadata.get("fruit_diameter_p_values_allowed", False))
        or _frame_flag_any(feature_frame, "fruit_diameter_p_values_allowed"),
        "fruit_diameter_allocation_calibration_target": bool(
            observer_metadata.get("fruit_diameter_allocation_calibration_target", False)
        )
        or _frame_flag_any(feature_frame, "fruit_diameter_allocation_calibration_target"),
        "fruit_diameter_model_promotion_target": bool(
            observer_metadata.get("fruit_diameter_model_promotion_target", False)
        )
        or _frame_flag_any(feature_frame, "fruit_diameter_model_promotion_target"),
        "direct_partition_observation_available": bool(
            observer_metadata.get("direct_partition_observation_available", False)
        )
        or _frame_flag_any(feature_frame, "direct_partition_observation_available"),
        "latent_allocation_directly_validated": bool(
            observer_metadata.get("latent_allocation_directly_validated", False)
        )
        or _frame_flag_any(feature_frame, "latent_allocation_directly_validated"),
    }


def _metadata_base(
    *,
    config: dict[str, Any],
    observer_metadata: dict[str, Any],
    feature_frame_path: Path,
    observer_metadata_path: Path,
    precondition_meta: dict[str, Any],
    input_state: pd.DataFrame | None = None,
    diagnostics: dict[str, Any] | None = None,
    guardrails: pd.DataFrame | None = None,
    prior_families_run: list[str] | None = None,
) -> dict[str, Any]:
    diagnostics = diagnostics or {}
    guardrail_map = _guardrail_pass_map(guardrails if guardrails is not None else pd.DataFrame())
    return {
        "season_id": SEASON_ID,
        "latent_allocation_pipeline_version": LATENT_ALLOCATION_PIPELINE_VERSION,
        "observer_feature_frame_path": str(feature_frame_path),
        "observer_metadata_path": str(observer_metadata_path),
        "production_observer_precondition_passed": bool(
            precondition_meta.get("production_observer_precondition_passed", False)
        ),
        "production_ready_for_latent_allocation_input": bool(
            observer_metadata.get("production_ready_for_latent_allocation", False)
        ),
        "row_cap_applied_input": bool(observer_metadata.get("row_cap_applied", False)),
        "radiation_daynight_primary_source": observer_metadata.get("radiation_daynight_primary_source", "dataset1"),
        "radiation_column_used": observer_metadata.get("radiation_column_used", "env_inside_radiation_wm2"),
        "fixed_clock_daynight_primary": False,
        "clock_06_18_used_only_for_compatibility": True,
        "latent_allocation_inference_run": bool(precondition_meta.get("production_observer_precondition_passed", False)),
        "latent_allocation_directly_validated": False,
        "direct_partition_observation_available": False,
        "allocation_validation_basis": "latent_inference_from_observer_features",
        "latent_allocation_promotable_by_itself": False,
        "prior_families_run": prior_families_run or list(PRIOR_FAMILIES),
        "raw_THORP_allocator_used": False,
        "THORP_used_as_bounded_prior": True,
        "THORP_used_as_raw_allocator": False,
        "THORP_fruit_gate_override_allowed": False,
        "fruit_diameter_p_values_allowed": False,
        "fruit_diameter_allocation_calibration_target": False,
        "fruit_diameter_model_promotion_target": False,
        "LAI_available": bool(input_state["LAI_available"].any()) if input_state is not None and "LAI_available" in input_state else False,
        "LAI_proxy_used": bool(input_state["LAI_proxy_available"].any())
        if input_state is not None and "LAI_proxy_available" in input_state
        else False,
        "apparent_canopy_conductance_available": bool(
            diagnostics.get(
                "apparent_conductance_available",
                observer_metadata.get("apparent_canopy_conductance_available", False),
            )
        ),
        "event_bridged_ET_calibration_status": observer_metadata.get(
            "event_bridged_ET_calibration_status",
            "unknown",
        ),
        "Dataset3_mapping_confidence": observer_metadata.get("Dataset3_mapping_confidence", "unknown"),
        "harvest_family_factorial_run": False,
        "promotion_gate_run": False,
        "cross_dataset_gate_run": False,
        "shipped_TOMICS_incumbent_changed": False,
        "diagnostic_statement": DIRECT_VALIDATION_STATEMENT,
        **precondition_meta,
        "latent_allocation_guardrails_passed": all(guardrail_map.values()) if guardrail_map else False,
        **guardrail_map,
    }


def _failure_outputs(
    *,
    output_root: Path,
    config: dict[str, Any],
    observer_metadata: dict[str, Any],
    feature_frame_path: Path,
    observer_metadata_path: Path,
    precondition_meta: dict[str, Any],
) -> dict[str, Any]:
    empty = pd.DataFrame()
    outputs = {
        "inputs": _write_csv(output_root, "inputs", empty),
        "priors": _write_csv(output_root, "priors", empty),
        "posteriors": _write_csv(output_root, "posteriors", empty),
        "diagnostics": _write_csv(output_root, "diagnostics", empty),
        "identifiability": _write_csv(output_root, "identifiability", empty),
        "guardrails": _write_csv(
            output_root,
            "guardrails",
            pd.DataFrame(
                [
                    {
                        "guardrail_name": "production_observer_precondition",
                        "status": "fail",
                        "pass_fail": False,
                        "violation_count": 1,
                        "max_violation": 1.0,
                        "affected_rows": "",
                        "notes": ",".join(precondition_meta.get("precondition_failure_reasons", [])),
                    }
                ]
            ),
        ),
    }
    metadata = _metadata_base(
        config=config,
        observer_metadata=observer_metadata,
        feature_frame_path=feature_frame_path,
        observer_metadata_path=observer_metadata_path,
        precondition_meta=precondition_meta | {"production_observer_precondition_passed": False},
    )
    metadata["latent_allocation_inference_run"] = False
    metadata["latent_allocation_ready"] = False
    metadata_path = output_root / OUTPUT_FILENAMES["metadata"]
    write_json(metadata_path, metadata)
    summary_path = _write_text(
        output_root,
        "summary",
        "# TOMICS-HAF 2025-2C Latent Allocation Inference\n\n"
        "Latent allocation inference was not run because production observer preconditions failed.\n\n"
        f"Failure reasons: {metadata.get('precondition_failure_reasons', [])}\n",
    )
    outputs["metadata"] = metadata_path
    outputs["summary"] = summary_path
    return {"outputs": {key: str(value) for key, value in outputs.items()}, "metadata": metadata}


def _summary_text(
    *,
    input_state: pd.DataFrame,
    priors: pd.DataFrame,
    posteriors: pd.DataFrame,
    identifiability: pd.DataFrame,
    guardrails: pd.DataFrame,
    metadata: dict[str, Any],
) -> str:
    guardrail_lines = [
        f"- {row.guardrail_name}: {row.status} ({int(row.violation_count)} violations)"
        for row in guardrails.itertuples(index=False)
    ]
    identifiability_score = (
        str(identifiability.iloc[0]["allocation_identifiability_score"]) if not identifiability.empty else "unknown"
    )
    return "\n".join(
        [
            "# TOMICS-HAF 2025-2C Latent Allocation Inference",
            "",
            "Latent allocation inference is an observer-supported inference layer, not direct allocation validation.",
            "THORP is used as a bounded mechanistic prior/correction, not as a raw tomato allocator.",
            "Day/night phases remain radiation-defined from Dataset1 env_inside_radiation_wm2, not fixed 06:00-18:00.",
            "Fruit diameter remains sensor-level apparent expansion diagnostics.",
            "Shipped TOMICS incumbent remains unchanged.",
            "",
            f"- Input rows: {input_state.shape[0]}",
            f"- Prior rows: {priors.shape[0]}",
            f"- Posterior rows: {posteriors.shape[0]}",
            f"- Prior families: {', '.join(metadata['prior_families_run'])}",
            f"- Identifiability score: {identifiability_score}",
            f"- Event-bridged ET calibration status: {metadata['event_bridged_ET_calibration_status']}",
            "",
            "## Guardrails",
            *guardrail_lines,
            "",
            f"## Diagnostic Statement\n\n{DIRECT_VALIDATION_STATEMENT}",
            "",
            "Harvest-family factorial, cross-dataset gate, and promotion gate remain unrun.",
        ]
    )


def run_tomics_haf_latent_allocation(config_path: str | Path) -> dict[str, Any]:
    config_path = Path(config_path).resolve()
    config = load_config(config_path)
    repo_root = _repo_root_from_config(config_path, config)
    tomics_haf = _tomics_haf_config(config)
    feature_frame_path = resolve_repo_path(repo_root, tomics_haf["observer_feature_frame"])
    observer_metadata_path = resolve_repo_path(repo_root, tomics_haf["observer_metadata"])
    output_root = resolve_repo_path(
        repo_root,
        tomics_haf.get("output_root", "out/tomics/validation/latent-allocation/haf_2025_2c"),
    )
    ensure_dir(output_root)

    observer_metadata = _read_json(observer_metadata_path)
    precondition_passed, precondition_meta = check_production_preconditions(observer_metadata, config)
    if not precondition_passed:
        return _failure_outputs(
            output_root=output_root,
            config=config,
            observer_metadata=observer_metadata,
            feature_frame_path=feature_frame_path,
            observer_metadata_path=observer_metadata_path,
            precondition_meta=precondition_meta,
        )

    feature_frame = pd.read_csv(feature_frame_path)
    input_state, input_meta = build_latent_allocation_input_state(feature_frame, observer_metadata, config)
    priors = build_latent_allocation_priors(input_state, config)
    posteriors = infer_latent_allocation(priors, config)
    identifiability = compute_allocation_identifiability(input_state, observer_metadata)
    support = compute_observer_support_scores(input_state, observer_metadata)
    diagnostics = compute_prior_family_diagnostics(priors, posteriors)
    for key, value in support.items():
        diagnostics[key] = value
    forbidden_metadata = _forbidden_contract_metadata(observer_metadata, feature_frame)
    guardrails = evaluate_latent_allocation_guardrails(posteriors, forbidden_metadata, config)
    prior_families_run = (
        list(priors["prior_family"].drop_duplicates())
        if "prior_family" in priors.columns and not priors.empty
        else []
    )

    metadata = _metadata_base(
        config=config,
        observer_metadata=observer_metadata,
        feature_frame_path=feature_frame_path,
        observer_metadata_path=observer_metadata_path,
        precondition_meta=input_meta,
        input_state=input_state,
        diagnostics=support,
        guardrails=guardrails,
        prior_families_run=prior_families_run,
    )
    metadata["latent_allocation_ready"] = True
    metadata["posterior_row_count"] = int(posteriors.shape[0])

    outputs = {
        "inputs": _write_csv(output_root, "inputs", input_state),
        "priors": _write_csv(output_root, "priors", priors),
        "posteriors": _write_csv(output_root, "posteriors", posteriors),
        "diagnostics": _write_csv(output_root, "diagnostics", diagnostics),
        "identifiability": _write_csv(output_root, "identifiability", identifiability),
        "guardrails": _write_csv(output_root, "guardrails", guardrails),
    }
    metadata_path = output_root / OUTPUT_FILENAMES["metadata"]
    write_json(metadata_path, metadata)
    summary_path = _write_text(
        output_root,
        "summary",
        _summary_text(
            input_state=input_state,
            priors=priors,
            posteriors=posteriors,
            identifiability=identifiability,
            guardrails=guardrails,
            metadata=metadata,
        ),
    )
    outputs["metadata"] = metadata_path
    outputs["summary"] = summary_path
    return {"outputs": {key: str(value) for key, value in outputs.items()}, "metadata": metadata}


__all__ = ["run_tomics_haf_latent_allocation"]
