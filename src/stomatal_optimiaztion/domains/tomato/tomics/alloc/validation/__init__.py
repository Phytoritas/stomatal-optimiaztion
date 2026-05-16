from __future__ import annotations

from importlib import import_module
from typing import Any


_EXPORTS: dict[str, tuple[str, str]] = {
    "AllocationLaneSpec": (".lane_matrix", "AllocationLaneSpec"),
    "CalibrationArtifacts": (".calibration", "CalibrationArtifacts"),
    "CalibrationBudget": (".parameter_budget", "CalibrationBudget"),
    "CalibrationSplit": (".calibration", "CalibrationSplit"),
    "CANONICAL_REPORTING_BASIS": (".datasets", "CANONICAL_REPORTING_BASIS"),
    "CandidateSpec": (".calibration", "CandidateSpec"),
    "CanonicalWinnerIds": (".artifact_sync", "CanonicalWinnerIds"),
    "ComparisonScenario": (".lane_matrix", "ComparisonScenario"),
    "DatasetBasisContract": (".datasets", "DatasetBasisContract"),
    "DatasetCapability": (".datasets", "DatasetCapability"),
    "DatasetIngestionStatus": (".datasets", "DatasetIngestionStatus"),
    "DatasetManagementMetadata": (".datasets", "DatasetManagementMetadata"),
    "DatasetMetadataContract": (".datasets", "DatasetMetadataContract"),
    "DatasetObservationContract": (".datasets", "DatasetObservationContract"),
    "DatasetRegistry": (".datasets", "DatasetRegistry"),
    "DatasetRoleSpec": (".lane_matrix", "DatasetRoleSpec"),
    "DatasetSanitizedFixtureContract": (".datasets", "DatasetSanitizedFixtureContract"),
    "DEFAULT_SCENARIOS": (".theta_proxy", "DEFAULT_SCENARIOS"),
    "HarvestProfileSpec": (".lane_matrix", "HarvestProfileSpec"),
    "KnuDataContractPaths": (".data_contract", "KnuDataContractPaths"),
    "KnuValidationData": (".knu_data", "KnuValidationData"),
    "PLANTS_PER_M2": (".knu_data", "PLANTS_PER_M2"),
    "PreparedDatasetThetaScenario": (".datasets", "PreparedDatasetThetaScenario"),
    "PreparedKnuBundle": (".current_vs_promoted", "PreparedKnuBundle"),
    "PreparedMeasuredHarvestBundle": (".datasets", "PreparedMeasuredHarvestBundle"),
    "PreparedThetaScenario": (".current_vs_promoted", "PreparedThetaScenario"),
    "REPORTING_BASIS_FLOOR_AREA": (".metrics", "REPORTING_BASIS_FLOOR_AREA"),
    "ReconstructionResult": (".state_reconstruction", "ReconstructionResult"),
    "ResolvedAllocationLane": (".lane_matrix", "ResolvedAllocationLane"),
    "ResolvedDatasetRole": (".lane_matrix", "ResolvedDatasetRole"),
    "RootzoneInversionResult": (".rootzone_inversion", "RootzoneInversionResult"),
    "ThetaProxyScenario": (".theta_proxy", "ThetaProxyScenario"),
    "TraitenvInventoryBundle": (".datasets", "TraitenvInventoryBundle"),
    "ValidationSeriesBundle": (".metrics", "ValidationSeriesBundle"),
    "apply_theta_substrate_proxy": (".theta_proxy", "apply_theta_substrate_proxy"),
    "build_calibration_budget": (".parameter_budget", "build_calibration_budget"),
    "build_calibration_splits": (".calibration", "build_calibration_splits"),
    "build_cross_dataset_guardrail_summary": (".cross_dataset_gate", "build_cross_dataset_guardrail_summary"),
    "build_cross_dataset_inventory_scorecard": (
        ".cross_dataset_scorecard",
        "build_cross_dataset_inventory_scorecard",
    ),
    "build_cross_dataset_scorecard": (".cross_dataset_scorecard", "build_cross_dataset_scorecard"),
    "build_haf_cross_dataset_gate_payload": (
        ".haf_cross_dataset_gate",
        "build_haf_cross_dataset_gate_payload",
    ),
    "build_haf_promotion_gate_payload": (".haf_promotion_gate", "build_haf_promotion_gate_payload"),
    "build_dataset_inventory_summary": (".datasets", "build_dataset_inventory_summary"),
    "build_traitenv_candidate_registry": (".datasets", "build_traitenv_candidate_registry"),
    "canopy_collapse_days": (".metrics", "canopy_collapse_days"),
    "compose_scenarios": (".lane_matrix", "compose_scenarios"),
    "compute_validation_bundle": (".metrics", "compute_validation_bundle"),
    "configure_candidate_run": (".current_vs_promoted", "configure_candidate_run"),
    "contract_payload": (".data_contract", "contract_payload"),
    "cross_dataset_proxy_guardrail": (".cross_dataset_gate", "cross_dataset_proxy_guardrail"),
    "daily_last": (".metrics", "daily_last"),
    "dataset_blocker_frame": (".datasets", "dataset_blocker_frame"),
    "dataset_metadata_payload": (".datasets", "dataset_metadata_payload"),
    "dataset_registry_frame": (".datasets", "dataset_registry_frame"),
    "default_allocation_lane_specs": (".lane_matrix", "default_allocation_lane_specs"),
    "derive_ingestion_status": (".datasets", "derive_ingestion_status"),
    "docs_reference_winners": (".artifact_sync", "docs_reference_winners"),
    "extract_winner_mentions": (".artifact_sync", "extract_winner_mentions"),
    "harvest_timing_mae_days": (".metrics", "harvest_timing_mae_days"),
    "infer_dataset_role": (".lane_matrix", "infer_dataset_role"),
    "intake_priority_rows": (".datasets", "intake_priority_rows"),
    "is_measured_harvest_runnable": (".datasets", "is_measured_harvest_runnable"),
    "load_candidate_specs": (".calibration", "load_candidate_specs"),
    "load_canonical_winner_ids": (".artifact_sync", "load_canonical_winner_ids"),
    "load_dataset_factorial_outputs": (".cross_dataset_scorecard", "load_dataset_factorial_outputs"),
    "load_dataset_registry": (".datasets", "load_dataset_registry"),
    "load_knu_validation_data": (".knu_data", "load_knu_validation_data"),
    "load_traitenv_inventory": (".datasets", "load_traitenv_inventory"),
    "measured_harvest_contract_satisfied": (".lane_matrix", "measured_harvest_contract_satisfied"),
    "missing_required_fields": (".datasets", "missing_required_fields"),
    "model_floor_area_cumulative_total_fruit": (".metrics", "model_floor_area_cumulative_total_fruit"),
    "observed_floor_area_yield": (".metrics", "observed_floor_area_yield"),
    "prepare_knu_bundle": (".current_vs_promoted", "prepare_knu_bundle"),
    "prepare_measured_harvest_bundle": (".datasets", "prepare_measured_harvest_bundle"),
    "read_dataset_observation_table": (".datasets", "read_dataset_observation_table"),
    "read_knu_forcing_csv": (".knu_data", "read_knu_forcing_csv"),
    "read_knu_yield_workbook": (".knu_data", "read_knu_yield_workbook"),
    "reconstruct_hidden_state": (".state_reconstruction", "reconstruct_hidden_state"),
    "reconstruct_rootzone": (".rootzone_inversion", "reconstruct_rootzone"),
    "resolve_allocation_lanes": (".lane_matrix", "resolve_allocation_lanes"),
    "resolve_dataset_roles": (".lane_matrix", "resolve_dataset_roles"),
    "resolve_harvest_profiles": (".lane_matrix", "resolve_harvest_profiles"),
    "resolve_knu_data_contract": (".data_contract", "resolve_knu_data_contract"),
    "resample_forcing": (".knu_data", "resample_forcing"),
    "run_calibration_suite": (".calibration", "run_calibration_suite"),
    "run_current_factorial_knu": (".current_vs_promoted", "run_current_factorial_knu"),
    "run_current_vs_promoted_factorial": (".current_vs_promoted", "run_current_vs_promoted_factorial"),
    "run_identifiability_analysis": (".identifiability", "run_identifiability_analysis"),
    "run_lane_matrix": (".lane_matrix", "run_lane_matrix"),
    "run_lane_matrix_gate": (".lane_matrix", "run_lane_matrix_gate"),
    "run_haf_cross_dataset_gate": (".haf_cross_dataset_gate", "run_haf_cross_dataset_gate"),
    "run_haf_promotion_gate": (".haf_promotion_gate", "run_haf_promotion_gate"),
    "run_promoted_factorial_knu": (".current_vs_promoted", "run_promoted_factorial_knu"),
    "run_promotion_gate": (".promotion_gate", "run_promotion_gate"),
    "theta_proxy_summary": (".theta_proxy", "theta_proxy_summary"),
    "to_floor_area_value": (".metrics", "to_floor_area_value"),
    "vpd_kpa_from_t_rh": (".theta_proxy", "vpd_kpa_from_t_rh"),
    "write_canonical_winner_manifest": (".artifact_sync", "write_canonical_winner_manifest"),
    "write_data_contract_manifest": (".data_contract", "write_data_contract_manifest"),
    "write_knu_manifest": (".knu_data", "write_knu_manifest"),
    "write_rootzone_manifest": (".rootzone_inversion", "write_rootzone_manifest"),
    "write_side_by_side_bundle": (".current_vs_promoted", "write_side_by_side_bundle"),
}

__all__ = sorted(_EXPORTS)


def __getattr__(name: str) -> Any:
    if name not in _EXPORTS:
        msg = f"module {__name__!r} has no attribute {name!r}"
        raise AttributeError(msg)
    module_name, attribute_name = _EXPORTS[name]
    value = getattr(import_module(module_name, __name__), attribute_name)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return sorted(set(globals()) | set(__all__))
