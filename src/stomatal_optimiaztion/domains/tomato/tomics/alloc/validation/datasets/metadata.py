from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.datasets.contracts import (
    DatasetBasisContract,
    DatasetCapability,
    DatasetIngestionStatus,
    DatasetManagementMetadata,
    DatasetMetadataContract,
    DatasetObservationContract,
    accepted_review_only_dry_matter_runtime,
    dataset_review_flags,
    is_measured_harvest_runnable,
)


def normalize_basis_metadata(
    *,
    reporting_basis: str | None = None,
    plants_per_m2: float | None = None,
) -> DatasetBasisContract:
    return DatasetBasisContract(reporting_basis=reporting_basis or "unknown", plants_per_m2=plants_per_m2)


def normalize_observation_metadata(
    *,
    date_column: str | None = None,
    measured_cumulative_column: str | None = None,
    estimated_cumulative_column: str | None = None,
    measured_semantics: str = "cumulative_harvested_fruit_dry_weight_floor_area",
    daily_increment_column: str | None = None,
) -> DatasetObservationContract:
    return DatasetObservationContract(
        date_column=date_column,
        measured_cumulative_column=measured_cumulative_column,
        estimated_cumulative_column=estimated_cumulative_column,
        measured_semantics=measured_semantics,
        daily_increment_column=daily_increment_column,
    )


def normalize_label(value: object, *, default: str = "unknown") -> str:
    text = str(value).strip() if value is not None else ""
    return text or default


def normalize_management_metadata(
    *,
    pruning_records_path: str | Path | None = None,
    defoliation_records_path: str | Path | None = None,
    harvest_timing_records_path: str | Path | None = None,
    irrigation_path: str | Path | None = None,
    ec_path: str | Path | None = None,
    rootzone_path: str | Path | None = None,
) -> DatasetManagementMetadata:
    def _maybe_path(raw: str | Path | None) -> Path | None:
        return Path(raw) if raw not in (None, "") else None

    return DatasetManagementMetadata(
        pruning_records_path=_maybe_path(pruning_records_path),
        defoliation_records_path=_maybe_path(defoliation_records_path),
        harvest_timing_records_path=_maybe_path(harvest_timing_records_path),
        irrigation_path=_maybe_path(irrigation_path),
        ec_path=_maybe_path(ec_path),
        rootzone_path=_maybe_path(rootzone_path),
    )


def dataset_metadata_payload(dataset: DatasetMetadataContract) -> dict[str, Any]:
    payload = dataset.to_payload()
    payload["management_record_count"] = int(
        sum(
            value is not None
            for value in (
                dataset.management.pruning_records_path,
                dataset.management.defoliation_records_path,
                dataset.management.harvest_timing_records_path,
                dataset.management.irrigation_path,
                dataset.management.ec_path,
                dataset.management.rootzone_path,
            )
        )
    )
    payload["has_management_records"] = dataset.has_management_records
    payload["is_runnable_measured_harvest"] = is_measured_harvest_runnable(dataset)
    payload["basis_normalization_resolved"] = dataset.basis.normalization_resolved
    return payload


def dataset_registry_frame(datasets: list[DatasetMetadataContract]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for dataset in datasets:
        payload = dataset_metadata_payload(dataset)
        rows.append(
            {
                "dataset_id": payload["dataset_id"],
                "dataset_kind": payload["dataset_kind"],
                "display_name": payload["display_name"],
                "dataset_family": payload["dataset_family"],
                "observation_family": payload["observation_family"],
                "capability": payload["capability"],
                "ingestion_status": payload["ingestion_status"],
                "is_runnable_measured_harvest": payload["is_runnable_measured_harvest"],
                "reporting_basis": payload["basis"]["reporting_basis"],
                "plants_per_m2": payload["basis"]["plants_per_m2"],
                "basis_unit_label": payload["basis"]["basis_unit_label"],
                "basis_normalization_resolved": payload["basis_normalization_resolved"],
                "validation_start": payload["validation_start"],
                "validation_end": payload["validation_end"],
                "date_column": payload["observation"]["date_column"],
                "measured_cumulative_column": payload["observation"]["measured_cumulative_column"],
                "dry_matter_conversion_mode": payload["dry_matter_conversion"]["mode"],
                "dry_matter_ratio": payload["dry_matter_conversion"]["dry_matter_ratio"],
                "dry_matter_ratio_low": payload["dry_matter_conversion"]["dry_matter_ratio_low"],
                "dry_matter_ratio_high": payload["dry_matter_conversion"]["dry_matter_ratio_high"],
                "dry_matter_conversion_review_only": payload["dry_matter_conversion"]["review_only"],
                "accepted_review_only_derived_dw_runtime": accepted_review_only_dry_matter_runtime(dataset),
                "observed_harvest_derivation": payload["notes"].get("observed_harvest_derivation"),
                "is_direct_dry_weight": payload["notes"].get("is_direct_dry_weight"),
                "uses_literature_dry_matter_fraction": payload["notes"].get(
                    "uses_literature_dry_matter_fraction"
                ),
                "review_flags": json.dumps(dataset_review_flags(dataset), sort_keys=True),
                "cultivar": payload["cultivar"],
                "greenhouse": payload["greenhouse"],
                "season": payload["season"],
                "source_refs": json.dumps(payload["source_refs"], sort_keys=True),
                "priority_tags": json.dumps(payload["priority_tags"], sort_keys=True),
                "blocker_codes": json.dumps(payload["blocker_codes"], sort_keys=True),
                "provenance_tags": json.dumps(payload["provenance_tags"], sort_keys=True),
                "has_management_records": payload["has_management_records"],
                "management_record_count": payload["management_record_count"],
                "forcing_path": payload["forcing_path"],
                "observed_harvest_path": payload["observed_harvest_path"],
                "sanitized_fixture_path": payload["sanitized_fixture_path"],
            }
        )
    return pd.DataFrame(rows)


def dataset_blocker_frame(datasets: list[DatasetMetadataContract]) -> pd.DataFrame:
    columns = [
        "dataset_id",
        "dataset_kind",
        "dataset_family",
        "observation_family",
        "capability",
        "ingestion_status",
        "blocker_code",
    ]
    rows: list[dict[str, Any]] = []
    for dataset in datasets:
        for blocker_code in dataset.blocker_codes:
            rows.append(
                {
                    "dataset_id": dataset.dataset_id,
                    "dataset_kind": dataset.dataset_kind,
                    "dataset_family": dataset.dataset_family,
                    "observation_family": dataset.observation_family,
                    "capability": dataset.capability.value,
                    "ingestion_status": dataset.ingestion_status.value,
                    "blocker_code": blocker_code,
                }
            )
    return pd.DataFrame(rows, columns=columns)


def dataset_blocker_rows(datasets: list[DatasetMetadataContract]) -> list[dict[str, Any]]:
    return dataset_blocker_frame(datasets).to_dict(orient="records")


BLOCKER_ACTIONS = {
    "missing_raw_fixture": "Add a reproducible raw-to-sanitized fixture path or sanitized fixture pair before promotion use.",
    "missing_forcing_path": "Declare a forcing source that covers the validation window.",
    "missing_observed_harvest_path": "Declare the observed harvest source for this dataset candidate.",
    "missing_sanitized_fixture": "Create or point to a sanitized forcing/harvest fixture pair.",
    "missing_reporting_basis": "Set reporting_basis explicitly and keep floor-area vs per-plant provenance explicit.",
    "missing_plants_per_m2": "Provide plants_per_m2 before any per-plant dataset can become runnable.",
    "missing_validation_window": "Set validation_start and validation_end for the measured-harvest window.",
    "missing_date_column": "Map the standardized observation date column explicitly.",
    "missing_measured_cumulative_column": (
        "Map or losslessly construct a cumulative harvested-fruit column from the standardized harvest signal."
    ),
    "ambiguous_harvest_semantics": (
        "Clarify that the measured target is cumulative harvested fruit dry weight, not latent or on-plant fruit mass."
    ),
}

DRY_MATTER_LITERATURE_REFS = (
    (
        "Ref 4",
        "General mature-fruit DW/FW reported at 5.917-6.495% in a conservative whole-fruit comparison.",
        "https://pmc.ncbi.nlm.nih.gov/articles/PMC11339430/",
    ),
    (
        "Ref 8",
        "Greenhouse destructive measurements reported mean fruit dry-matter fraction 5.6%, range 4.9-6.9%.",
        "https://linkinghub.elsevier.com/retrieve/pii/030442389400729Y",
    ),
    (
        "Ref 3",
        "Supplemental-light greenhouse tomatoes spanned 4.6-11.3%; larger-fruit lines centered near 6.6%, cherry near 9.5%.",
        "https://pmc.ncbi.nlm.nih.gov/articles/PMC8980428/",
    ),
    (
        "Ref 6",
        "Cherry tomato dry-matter fraction reached 8.2-13.9% under genotype/storage comparisons.",
        "https://pmc.ncbi.nlm.nih.gov/articles/PMC7760833/",
    ),
    (
        "Ref 7",
        "Greenhouse drought treatment shifted fruit DW/FW upward to about 9.30-9.72%.",
        "https://pmc.ncbi.nlm.nih.gov/articles/PMC12251554/",
    ),
    (
        "Ref 9",
        "Mechanistic fruit-growth analysis reported maturity water content near 95%, supporting a review-only prior near 5% dry matter with condition-dependent spread.",
        "https://academic.oup.com/jxb/article-lookup/doi/10.1093/jxb/erm202",
    ),
)


def blocker_action_items(blocker_codes: list[str] | tuple[str, ...]) -> list[str]:
    actions: list[str] = []
    for blocker_code in blocker_codes:
        action = BLOCKER_ACTIONS.get(str(blocker_code))
        if action is not None and action not in actions:
            actions.append(action)
    return actions


def _source_ref_preview(dataset: DatasetMetadataContract, *, limit: int = 3) -> str:
    preview_refs = [str(ref) for ref in dataset.source_refs[:limit] if str(ref).strip()]
    if not preview_refs:
        return "no source refs recorded in the current inventory snapshot"
    preview = "; ".join(preview_refs)
    if len(dataset.source_refs) > limit:
        preview += "; ..."
    return preview


def _default_basis_provenance_note(dataset: DatasetMetadataContract) -> str:
    if dataset.basis.reporting_basis != "unknown":
        return (
            f"Reviewed basis is currently `{dataset.basis.reporting_basis}`. "
            "Keep this provenance explicit if the dataset later becomes runnable."
        )
    partition_path = dataset.notes.get("candidate_partition_integrated_observations_path")
    basis_fields_present = list(dataset.notes.get("candidate_basis_fields_present", []))
    basis_fields_missing = list(dataset.notes.get("candidate_basis_fields_missing", []))
    if partition_path and not basis_fields_present and basis_fields_missing:
        return (
            "Inventory-derived candidate only. Harmonized observation partition "
            f"`{partition_path}` does not yet provide non-null basis evidence in `{basis_fields_missing}`. "
            "Reporting basis remains unresolved and must be reviewed from upstream source metadata before promotion use."
        )
    if partition_path and basis_fields_present:
        return (
            "Inventory-derived candidate only. Harmonized observation partition "
            f"`{partition_path}` exposes candidate basis-related fields `{basis_fields_present}`, but the reporting basis "
            "still needs explicit review before promotion use."
        )
    return (
        "Inventory-derived candidate only. Reporting basis is still unresolved and must be reviewed directly "
        f"from the source files before promotion use. Source preview: {_source_ref_preview(dataset)}."
    )


def _default_cumulative_mapping_note(dataset: DatasetMetadataContract) -> str:
    candidate_date_key = dataset.notes.get("candidate_date_key")
    candidate_harvest_column = dataset.notes.get("candidate_harvest_column")
    semantics_hint = dataset.notes.get("candidate_target_semantics_hint", dataset.observation.measured_semantics)
    preferred_season = dataset.notes.get("candidate_preferred_validation_season")
    preferred_window = dataset.notes.get("candidate_preferred_validation_window")
    construction_hint = dataset.notes.get("candidate_cumulative_construction_hint")
    preferred_window_note = ""
    if preferred_season is not None and isinstance(preferred_window, dict):
        start = preferred_window.get("validation_start_candidate")
        end = preferred_window.get("validation_end_candidate")
        row_count = preferred_window.get("harvest_row_count")
        preferred_window_note = (
            f" Preferred intake season is `{preferred_season}` with candidate window `{start}` -> `{end}` "
            f"and `{row_count}` comparison rows."
        )
    construction_note = f" {construction_hint}" if construction_hint else ""
    if candidate_harvest_column is not None:
        return (
            f"Candidate date hint `{candidate_date_key}` and daily harvest signal `{candidate_harvest_column}` are "
            f"visible in the harmonized inventory, but `measured_cumulative_column` must remain unresolved until "
            f"review confirms a valid cumulative-harvest construction and explicit dry-weight/public-basis semantics. "
            f"Current semantics hint: `{semantics_hint}`.{preferred_window_note}{construction_note}"
        )
    if candidate_date_key is not None:
        return (
            f"Candidate date hint `{candidate_date_key}` is visible, but no direct standardized harvest signal is "
            f"currently mapped for cumulative comparison. Keep `measured_cumulative_column` unresolved until a "
            f"reviewed harvest source and construction rule are added. Current semantics hint: `{semantics_hint}`."
            f"{preferred_window_note}"
        )
    return (
        "No reviewed date/cumulative mapping is currently available in the inventory-derived contract. "
        f"Current semantics hint: `{semantics_hint}`."
    )


def _default_fixture_provenance_note(dataset: DatasetMetadataContract) -> str:
    return (
        "This candidate is still inventory-backed only. Add a reproducible raw-to-sanitized fixture pair and wire "
        "`forcing_path`, `observed_harvest_path`, and `sanitized_fixture` before promoting it beyond review/diagnostic "
        f"use. Source preview: {_source_ref_preview(dataset)}."
    )


def _default_dry_matter_review_note(dataset: DatasetMetadataContract) -> str | None:
    semantics_hint = str(
        dataset.notes.get("candidate_target_semantics_hint", dataset.observation.measured_semantics)
    ).lower()
    if "dry_weight" not in semantics_hint:
        return None
    return (
        "Review-only dry-matter prior: literature synthesis for whole-fruit tomato typically centers near "
        "`5-8% DW/FW`, with fresh-market fruit commonly around `6-7%` and a practical review baseline near "
        "`0.065 g DW / g FW`; cherry/high-solids or stress cases can shift upward toward `8-10%` or higher. "
        "Keep these values as review guidance only and do not auto-convert this candidate from fresh-weight or "
        "removed-fruit-weight signals into cumulative harvested dry weight until dataset-specific source semantics "
        "are reviewed explicitly. [Ref 4][Ref 8][Ref 3][Ref 6][Ref 7][Ref 9]"
    )


def _dry_matter_literature_refs(dataset: DatasetMetadataContract) -> list[str]:
    if _default_dry_matter_review_note(dataset) is None:
        return []
    return [f"[{ref_id}] {summary} {url}" for ref_id, summary, url in DRY_MATTER_LITERATURE_REFS]


def build_dataset_review_template(dataset: DatasetMetadataContract) -> dict[str, Any]:
    payload = dataset.to_payload()
    dry_matter_review_note = _default_dry_matter_review_note(dataset)
    candidate_schema_hints = {
        key: payload["notes"][key]
        for key in (
            "candidate_date_key",
            "candidate_raw_date_columns",
            "candidate_harvest_column",
            "candidate_raw_harvest_columns",
            "candidate_harvest_requires_cumulative_construction",
            "candidate_harvest_includes_fallen_fruit",
            "candidate_target_semantics_hint",
            "candidate_requires_dry_weight_review",
            "candidate_validation_windows",
            "candidate_preferred_validation_season",
            "candidate_preferred_validation_window",
            "candidate_cumulative_group_keys",
            "candidate_cumulative_construction_hint",
            "candidate_seasons_missing_harvest_signal",
            "candidate_partition_integrated_observations_path",
            "candidate_partition_integrated_measurements_long_path",
            "candidate_partition_comparison_daily_path",
            "candidate_basis_fields_present",
            "candidate_basis_fields_missing",
            "comparison_daily_standard_names",
            "traitenv_bundle_ref",
        )
        if key in payload["notes"]
    }
    return {
        "dataset_id": dataset.dataset_id,
        "dataset_family": dataset.dataset_family,
        "observation_family": dataset.observation_family,
        "capability": dataset.capability.value,
        "ingestion_status": dataset.ingestion_status.value,
        "source_refs": list(dataset.source_refs),
        "blocker_codes": list(dataset.blocker_codes),
        "next_actions": blocker_action_items(dataset.blocker_codes),
        "candidate_schema_hints": candidate_schema_hints,
        "dry_matter_conversion": payload["dry_matter_conversion"],
        "promotion_ready_checklist": {
            "forcing_path": dataset.forcing_path is not None,
            "observed_harvest_path": dataset.observed_harvest_path is not None,
            "validation_window": bool(dataset.validation_start and dataset.validation_end),
            "reporting_basis": dataset.basis.reporting_basis != "unknown",
            "plants_per_m2": (
                True if not dataset.basis.requires_plant_density else dataset.basis.plants_per_m2 is not None
            ),
            "date_column": dataset.observation.date_column is not None,
            "daily_increment_column": dataset.observation.daily_increment_column is not None,
            "measured_cumulative_column": dataset.observation.measured_cumulative_column is not None,
            "harvest_semantics_explicit": "cumulative_harvested" in dataset.observation.measured_semantics.lower(),
            "sanitized_fixture_pair": dataset.sanitized_fixture.is_complete,
        },
        "review_updates": {
            "forcing_path": payload["forcing_path"],
            "observed_harvest_path": payload["observed_harvest_path"],
            "validation_start": payload["validation_start"],
            "validation_end": payload["validation_end"],
            "basis": {
                "reporting_basis": payload["basis"]["reporting_basis"],
                "plants_per_m2": payload["basis"]["plants_per_m2"],
            },
            "dry_matter_conversion": payload["dry_matter_conversion"],
            "observation": {
                "date_column": payload["observation"]["date_column"],
                "measured_cumulative_column": payload["observation"]["measured_cumulative_column"],
                "estimated_cumulative_column": payload["observation"]["estimated_cumulative_column"],
                "daily_increment_column": payload["observation"]["daily_increment_column"],
                "measured_semantics": payload["observation"]["measured_semantics"],
            },
            "sanitized_fixture": {
                "forcing_fixture_path": payload["sanitized_fixture"]["forcing_fixture_path"],
                "observed_harvest_fixture_path": payload["sanitized_fixture"]["observed_harvest_fixture_path"],
            },
            "notes": {
                "review_status": "todo",
                "basis_provenance_note": _default_basis_provenance_note(dataset),
                "cumulative_mapping_note": _default_cumulative_mapping_note(dataset),
                "fixture_provenance_note": _default_fixture_provenance_note(dataset),
                **(
                    {
                        "dry_matter_review_note": dry_matter_review_note,
                        "dry_matter_literature_refs": _dry_matter_literature_refs(dataset),
                    }
                    if dry_matter_review_note is not None
                    else {}
                ),
            },
        },
    }


def build_dataset_blocker_report(datasets: list[DatasetMetadataContract]) -> str:
    summary = build_dataset_inventory_summary(datasets)
    measured_candidates = [
        dataset
        for dataset in datasets
        if dataset.capability is DatasetCapability.MEASURED_HARVEST and not dataset.is_runnable_measured_harvest
    ]
    proxy_candidates = [
        dataset for dataset in datasets if dataset.capability is DatasetCapability.HARVEST_PROXY
    ]
    lines = [
        "# Dataset Intake Blocker Report",
        "",
        f"Total registry datasets: {summary['total_registry_datasets']}",
        f"Runnable measured-harvest datasets: {summary['runnable_measured_harvest_datasets']}",
        f"Measured-harvest candidates still blocked: {len(measured_candidates)}",
        f"Harvest-proxy candidates: {len(proxy_candidates)}",
        "",
    ]
    if not measured_candidates and not proxy_candidates:
        lines.extend(
            [
                "No blocked measured-harvest or harvest-proxy candidates are present in the registry.",
                "",
            ]
        )
        return "\n".join(lines)
    for dataset in measured_candidates:
        lines.extend(
            [
                f"## {dataset.dataset_id}",
                f"- capability: `{dataset.capability.value}`",
                f"- ingestion_status: `{dataset.ingestion_status.value}`",
                f"- blocker_codes: `{', '.join(dataset.blocker_codes)}`",
            ]
        )
        for action in blocker_action_items(dataset.blocker_codes):
            lines.append(f"- next_action: {action}")
        if dataset.observation.date_column is not None:
            lines.append(f"- schema_hint: standardized date column `{dataset.observation.date_column}` is already identified.")
        elif dataset.notes.get("candidate_raw_date_columns"):
            raw_date_columns = ", ".join(f"`{value}`" for value in dataset.notes["candidate_raw_date_columns"])
            lines.append(f"- schema_hint: raw date-like columns {raw_date_columns} were detected in the source inventory and still need explicit standardization review.")
        candidate_harvest_column = dataset.observation.daily_increment_column or dataset.notes.get("candidate_harvest_column")
        if candidate_harvest_column is not None:
            lines.append(
                f"- schema_hint: standardized daily harvest signal `{candidate_harvest_column}` is available but cumulative mapping is not yet resolved."
            )
        elif dataset.notes.get("candidate_raw_harvest_columns"):
            raw_harvest_columns = ", ".join(f"`{value}`" for value in dataset.notes["candidate_raw_harvest_columns"])
            lines.append(
                f"- schema_hint: raw harvest-like columns {raw_harvest_columns} were detected in the source inventory but are not yet promoted to a standardized cumulative target."
            )
        if "ambiguous_harvest_semantics" in dataset.blocker_codes:
            lines.append(
                f"- semantics_hint: `{dataset.notes.get('candidate_target_semantics_hint', dataset.observation.measured_semantics)}` still needs an explicit dry-weight or approved equivalent mapping."
            )
        lines.append("")
    for dataset in proxy_candidates:
        lines.extend(
            [
                f"## {dataset.dataset_id}",
                f"- capability: `{dataset.capability.value}`",
                f"- ingestion_status: `{dataset.ingestion_status.value}`",
                "- next_action: keep this dataset out of the measured-harvest promotion denominator until an explicit cumulative harvest contract exists.",
                "",
            ]
        )
    return "\n".join(lines)


def intake_priority_rows(datasets: list[DatasetMetadataContract]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for dataset in datasets:
        rows.append(
            {
                "dataset_id": dataset.dataset_id,
                "display_name": dataset.display_name,
                "dataset_family": dataset.dataset_family,
                "observation_family": dataset.observation_family,
                "capability": dataset.capability.value,
                "ingestion_status": dataset.ingestion_status.value,
                "is_runnable_measured_harvest": is_measured_harvest_runnable(dataset),
                "has_management_records": dataset.has_management_records,
                "has_irrigation_or_rootzone": any(
                    value is not None
                    for value in (
                        dataset.management.irrigation_path,
                        dataset.management.ec_path,
                        dataset.management.rootzone_path,
                    )
                ),
                "priority_tags": list(dataset.priority_tags),
                "blocker_codes": list(dataset.blocker_codes),
            }
        )
    return rows


def build_dataset_inventory_summary(datasets: list[DatasetMetadataContract]) -> dict[str, Any]:
    total_registry_datasets = len(datasets)
    capability_counts = {
        capability.value: sum(dataset.capability is capability for dataset in datasets)
        for capability in DatasetCapability
    }
    ingestion_status_counts = {
        status.value: sum(dataset.ingestion_status is status for dataset in datasets)
        for status in DatasetIngestionStatus
    }
    return {
        "total_registry_datasets": total_registry_datasets,
        "runnable_measured_harvest_datasets": sum(is_measured_harvest_runnable(dataset) for dataset in datasets),
        "proxy_datasets": capability_counts[DatasetCapability.HARVEST_PROXY.value],
        "context_only_datasets": capability_counts[DatasetCapability.CONTEXT_ONLY.value],
        "blocked_by_missing_raw_fixture": sum(
            "missing_raw_fixture" in dataset.blocker_codes
            or "missing_forcing_path" in dataset.blocker_codes
            or "missing_observed_harvest_path" in dataset.blocker_codes
            or "missing_sanitized_fixture" in dataset.blocker_codes
            for dataset in datasets
        ),
        "blocked_by_missing_basis_or_density": sum(
            "missing_reporting_basis" in dataset.blocker_codes or "missing_plants_per_m2" in dataset.blocker_codes
            for dataset in datasets
        ),
        "blocked_by_missing_cumulative_mapping": sum(
            "missing_validation_window" in dataset.blocker_codes
            or "missing_date_column" in dataset.blocker_codes
            or "missing_measured_cumulative_column" in dataset.blocker_codes
            or "ambiguous_harvest_semantics" in dataset.blocker_codes
            for dataset in datasets
        ),
        "capability_counts": capability_counts,
        "ingestion_status_counts": ingestion_status_counts,
    }


def registry_capability_summary(datasets: list[DatasetMetadataContract]) -> dict[str, Any]:
    return build_dataset_inventory_summary(datasets)


__all__ = [
    "BLOCKER_ACTIONS",
    "blocker_action_items",
    "build_dataset_review_template",
    "build_dataset_inventory_summary",
    "build_dataset_blocker_report",
    "dataset_blocker_frame",
    "dataset_blocker_rows",
    "dataset_metadata_payload",
    "dataset_registry_frame",
    "intake_priority_rows",
    "normalize_basis_metadata",
    "normalize_label",
    "normalize_management_metadata",
    "normalize_observation_metadata",
    "registry_capability_summary",
]
