from __future__ import annotations

import json
from typing import Any

import pandas as pd

from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.datasets.contracts import (
    DatasetMetadataContract,
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
                "reporting_basis": payload["basis"]["reporting_basis"],
                "plants_per_m2": payload["basis"]["plants_per_m2"],
                "basis_unit_label": payload["basis"]["basis_unit_label"],
                "validation_start": payload["validation_start"],
                "validation_end": payload["validation_end"],
                "cultivar": payload["cultivar"],
                "greenhouse": payload["greenhouse"],
                "season": payload["season"],
                "priority_tags": json.dumps(payload["priority_tags"], sort_keys=True),
                "has_management_records": payload["has_management_records"],
                "management_record_count": payload["management_record_count"],
                "forcing_path": payload["forcing_path"],
                "observed_harvest_path": payload["observed_harvest_path"],
            }
        )
    return pd.DataFrame(rows)


def intake_priority_rows(datasets: list[DatasetMetadataContract]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for dataset in datasets:
        rows.append(
            {
                "dataset_id": dataset.dataset_id,
                "display_name": dataset.display_name,
                "priority_tags": list(dataset.priority_tags),
                "has_management_records": dataset.has_management_records,
                "has_irrigation_or_rootzone": any(
                    value is not None
                    for value in (
                        dataset.management.irrigation_path,
                        dataset.management.ec_path,
                        dataset.management.rootzone_path,
                    )
                ),
            }
        )
    return rows


__all__ = ["dataset_metadata_payload", "dataset_registry_frame", "intake_priority_rows"]
