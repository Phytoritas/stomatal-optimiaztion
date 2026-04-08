from __future__ import annotations

from pathlib import Path
import json

import yaml

from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.datasets.contracts import (
    DatasetBasisContract,
    DatasetCapability,
    DatasetIngestionStatus,
    DatasetMetadataContract,
    DatasetObservationContract,
    DatasetSanitizedFixtureContract,
)
from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.datasets.registry import (
    DatasetRegistry,
    load_dataset_registry,
)


def _dataset(
    dataset_id: str,
    *,
    capability: DatasetCapability,
    ingestion_status: DatasetIngestionStatus,
    observation_family: str = "yield",
    reporting_basis: str = "floor_area_g_m2",
    plants_per_m2: float | None = 1.7,
    blocker_codes: tuple[str, ...] = (),
) -> DatasetMetadataContract:
    kwargs: dict[str, object] = {
        "dataset_id": dataset_id,
        "dataset_kind": "fixture",
        "display_name": dataset_id,
        "dataset_family": "fixture_family",
        "observation_family": observation_family,
        "capability": capability,
        "ingestion_status": ingestion_status,
        "basis": DatasetBasisContract(reporting_basis=reporting_basis, plants_per_m2=plants_per_m2),
        "observation": DatasetObservationContract(
            date_column="date" if capability is DatasetCapability.MEASURED_HARVEST else None,
            measured_cumulative_column="measured" if capability is DatasetCapability.MEASURED_HARVEST else None,
        ),
        "blocker_codes": blocker_codes,
    }
    if capability is DatasetCapability.MEASURED_HARVEST and ingestion_status is DatasetIngestionStatus.RUNNABLE:
        kwargs.update(
            forcing_path="forcing.csv",
            observed_harvest_path="harvest.csv",
            validation_start="2025-01-01",
            validation_end="2025-01-31",
            sanitized_fixture=DatasetSanitizedFixtureContract(
                forcing_fixture_path="forcing.csv",
                observed_harvest_fixture_path="harvest.csv",
            ),
        )
    return DatasetMetadataContract(**kwargs)


def test_dataset_registry_loads_explicit_items(tmp_path: Path) -> None:
    config = {
        "validation": {
            "datasets": {
                "default_dataset_ids": ["demo"],
                "items": [
                    {
                        "dataset_id": "demo",
                        "dataset_kind": "fixture",
                        "display_name": "Demo",
                        "forcing_path": "forcing.csv",
                        "observed_harvest_path": "harvest.csv",
                        "validation_start": "2025-01-01",
                        "validation_end": "2025-01-31",
                        "cultivar": "cv",
                        "greenhouse": "gh",
                        "season": "winter",
                        "basis": {"reporting_basis": "floor_area_g_m2", "plants_per_m2": 1.7},
                        "observation": {
                            "date_column": "date",
                            "measured_cumulative_column": "measured",
                        },
                        "priority_tags": ["baseline_window"],
                    }
                ],
            }
        }
    }
    config_path = tmp_path / "config.yaml"
    config_path.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")
    registry = load_dataset_registry(config, repo_root=tmp_path, config_path=config_path)
    assert registry.default_dataset_ids == ("demo",)
    assert registry.require("demo").dataset_kind == "fixture"
    assert registry.to_frame().shape[0] == 1


def test_dataset_registry_loads_snapshot_and_filters_runnable_measured_harvest(tmp_path: Path) -> None:
    snapshot_path = tmp_path / "snapshot.json"
    snapshot_payload = {
        "default_dataset_ids": [],
        "datasets": [
            {
                "dataset_id": "measured_demo",
                "dataset_kind": "fixture",
                "display_name": "Measured Demo",
                "dataset_family": "public_rda",
                "observation_family": "yield",
                "capability": "measured_harvest",
                "ingestion_status": "runnable",
                "forcing_path": "forcing.csv",
                "observed_harvest_path": "harvest.csv",
                "validation_start": "2025-01-01",
                "validation_end": "2025-01-31",
                "basis": {"reporting_basis": "floor_area_g_m2", "plants_per_m2": 1.7},
                "observation": {"date_column": "date", "measured_cumulative_column": "measured"},
                "sanitized_fixture": {
                    "forcing_fixture_path": "forcing.csv",
                    "observed_harvest_fixture_path": "harvest.csv",
                },
            },
            {
                "dataset_id": "proxy_demo",
                "dataset_kind": "traitenv_candidate",
                "display_name": "Proxy Demo",
                "dataset_family": "public_bigdata_platform",
                "observation_family": "yield_environment",
                "capability": "harvest_proxy",
                "ingestion_status": "draft_needs_raw_fixture",
                "blocker_codes": ["missing_raw_fixture"],
            },
        ],
    }
    (tmp_path / "forcing.csv").write_text("datetime,T_air_C\n2025-01-01,24\n", encoding="utf-8")
    (tmp_path / "harvest.csv").write_text("date,measured\n2025-01-01,1.0\n", encoding="utf-8")
    snapshot_path.write_text(json.dumps(snapshot_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    config = {"validation": {"datasets": {"registry_snapshot_path": str(snapshot_path)}}}
    config_path = tmp_path / "config.yaml"
    config_path.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")

    registry = load_dataset_registry(config, repo_root=tmp_path, config_path=config_path)

    assert registry.default_dataset_ids == ("measured_demo",)
    assert [dataset.dataset_id for dataset in registry.runnable_measured_harvest_datasets()] == ["measured_demo"]
    assert [dataset.dataset_id for dataset in registry.draft_datasets()] == ["proxy_demo"]


def test_dataset_registry_lists_capabilities_and_separates_drafts_from_runnable_denominator() -> None:
    registry = DatasetRegistry(
        datasets=(
            _dataset(
                "measured_live",
                capability=DatasetCapability.MEASURED_HARVEST,
                ingestion_status=DatasetIngestionStatus.RUNNABLE,
            ),
            _dataset(
                "measured_basis_blocked",
                capability=DatasetCapability.MEASURED_HARVEST,
                ingestion_status=DatasetIngestionStatus.DRAFT_NEEDS_BASIS_METADATA,
                reporting_basis="unknown",
                plants_per_m2=None,
                blocker_codes=("missing_reporting_basis",),
            ),
            _dataset(
                "proxy_demo",
                capability=DatasetCapability.HARVEST_PROXY,
                ingestion_status=DatasetIngestionStatus.DRAFT_NEEDS_RAW_FIXTURE,
                observation_family="yield_environment",
                reporting_basis="unknown",
                plants_per_m2=None,
                blocker_codes=("missing_raw_fixture",),
            ),
            _dataset(
                "context_demo",
                capability=DatasetCapability.CONTEXT_ONLY,
                ingestion_status=DatasetIngestionStatus.RUNNABLE,
                observation_family="environment",
                reporting_basis="unknown",
                plants_per_m2=None,
            ),
        ),
        default_dataset_ids=("measured_live",),
    )

    assert [dataset.dataset_id for dataset in registry.list_by_capability(DatasetCapability.MEASURED_HARVEST.value)] == [
        "measured_live",
        "measured_basis_blocked",
    ]
    assert [dataset.dataset_id for dataset in registry.runnable_measured_harvest_datasets()] == ["measured_live"]
    assert [dataset.dataset_id for dataset in registry.draft_datasets()] == [
        "measured_basis_blocked",
        "proxy_demo",
    ]
    blocker_frame = registry.blocker_frame()
    assert set(blocker_frame["dataset_id"]) == {"measured_basis_blocked", "proxy_demo", "context_demo"}


def test_dataset_registry_can_ignore_missing_optional_snapshot(tmp_path: Path) -> None:
    config = {
        "validation": {
            "datasets": {
                "registry_snapshot_path": "configs/data/tomics_multidataset_candidates/traitenv_candidate_registry.json",
                "allow_missing_registry_snapshot": True,
                "default_dataset_ids": ["demo"],
                "items": [
                    {
                        "dataset_id": "demo",
                        "dataset_kind": "fixture",
                        "display_name": "Demo",
                        "forcing_path": "forcing.csv",
                        "observed_harvest_path": "harvest.csv",
                        "validation_start": "2025-01-01",
                        "validation_end": "2025-01-31",
                        "basis": {"reporting_basis": "floor_area_g_m2", "plants_per_m2": 1.7},
                        "observation": {
                            "date_column": "date",
                            "measured_cumulative_column": "measured",
                        },
                    }
                ],
            }
        }
    }
    config_path = tmp_path / "config.yaml"
    config_path.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")

    registry = load_dataset_registry(config, repo_root=tmp_path, config_path=config_path)

    assert registry.default_dataset_ids == ("demo",)
    assert [dataset.dataset_id for dataset in registry.datasets] == ["demo"]


def test_dataset_registry_snapshot_nonexistent_paths_do_not_become_runnable(tmp_path: Path) -> None:
    snapshot_path = tmp_path / "snapshot.json"
    snapshot_payload = {
        "default_dataset_ids": [],
        "datasets": [
            {
                "dataset_id": "paper_only",
                "dataset_kind": "fixture",
                "display_name": "Paper Only",
                "dataset_family": "public_rda",
                "observation_family": "yield",
                "capability": "measured_harvest",
                "ingestion_status": "runnable",
                "forcing_path": "missing_forcing.csv",
                "observed_harvest_path": "missing_harvest.csv",
                "validation_start": "2025-01-01",
                "validation_end": "2025-01-31",
                "basis": {"reporting_basis": "floor_area_g_m2", "plants_per_m2": 1.7},
                "observation": {"date_column": "date", "measured_cumulative_column": "measured"},
                "sanitized_fixture": {
                    "forcing_fixture_path": "missing_forcing.csv",
                    "observed_harvest_fixture_path": "missing_harvest.csv",
                },
            }
        ],
    }
    snapshot_path.write_text(json.dumps(snapshot_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    config = {"validation": {"datasets": {"registry_snapshot_path": str(snapshot_path)}}}
    config_path = tmp_path / "config.yaml"
    config_path.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")

    registry = load_dataset_registry(config, repo_root=tmp_path, config_path=config_path)
    dataset = registry.require("paper_only")

    assert dataset.forcing_path is None
    assert dataset.observed_harvest_path is None
    assert dataset.sanitized_fixture.is_complete is False
    assert [item.dataset_id for item in registry.runnable_measured_harvest_datasets()] == []


def test_dataset_registry_explicit_items_overlay_snapshot_rows_instead_of_replacing_them(tmp_path: Path) -> None:
    snapshot_path = tmp_path / "snapshot.json"
    forcing_path = tmp_path / "forcing.csv"
    harvest_path = tmp_path / "harvest.csv"
    forcing_path.write_text("datetime,T_air_C\n2025-01-01,24\n", encoding="utf-8")
    harvest_path.write_text("date,measured\n2025-01-01,1.0\n", encoding="utf-8")
    snapshot_payload = {
        "default_dataset_ids": [],
        "datasets": [
            {
                "dataset_id": "review_candidate",
                "dataset_kind": "traitenv_candidate",
                "display_name": "Review Candidate",
                "dataset_family": "public_rda",
                "observation_family": "yield",
                "capability": "measured_harvest",
                "ingestion_status": "draft_needs_harvest_mapping",
                "source_refs": ["bundle/yield.csv"],
                "forcing_path": "forcing.csv",
                "observed_harvest_path": "harvest.csv",
                "validation_start": "2025-01-01",
                "validation_end": "2025-01-31",
                "basis": {"reporting_basis": "floor_area_g_m2", "plants_per_m2": 1.7},
                "observation": {"date_column": "date", "measured_cumulative_column": None},
                "sanitized_fixture": {
                    "forcing_fixture_path": "forcing.csv",
                    "observed_harvest_fixture_path": "harvest.csv",
                },
                "notes": {"candidate_harvest_column": "total_yield_weight_g"},
                "provenance_tags": ["traitenv"],
            }
        ],
    }
    snapshot_path.write_text(json.dumps(snapshot_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    config = {
        "validation": {
            "datasets": {
                "registry_snapshot_path": str(snapshot_path),
                "items": [
                    {
                        "dataset_id": "review_candidate",
                        "greenhouse": "demo-house",
                        "observation": {"measured_cumulative_column": "measured"},
                    }
                ],
            }
        }
    }
    config_path = tmp_path / "config.yaml"
    config_path.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")

    registry = load_dataset_registry(config, repo_root=tmp_path, config_path=config_path)
    dataset = registry.require("review_candidate")

    assert dataset.dataset_family == "public_rda"
    assert dataset.greenhouse == "demo-house"
    assert dataset.source_refs == ("bundle/yield.csv",)
    assert dataset.notes["candidate_harvest_column"] == "total_yield_weight_g"
    assert dataset.observation.measured_cumulative_column == "measured"
    assert dataset.sanitized_fixture.is_complete is True
