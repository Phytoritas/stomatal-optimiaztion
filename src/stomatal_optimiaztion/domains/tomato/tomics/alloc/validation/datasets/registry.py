from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any

import pandas as pd

from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.data_contract import (
    resolve_knu_data_contract,
)
from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.datasets.contracts import (
    DatasetBasisContract,
    DatasetCapability,
    DatasetIngestionStatus,
    DatasetManagementMetadata,
    DatasetMetadataContract,
    DatasetObservationContract,
    DatasetSanitizedFixtureContract,
    is_measured_harvest_runnable,
)
from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.datasets.metadata import (
    dataset_blocker_frame,
    build_dataset_inventory_summary,
    dataset_registry_frame,
)
from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.knu_data import (
    load_knu_validation_data,
)


def _as_dict(raw: object) -> dict[str, Any]:
    if isinstance(raw, dict):
        return {str(key): value for key, value in raw.items()}
    return {}


def _as_list(raw: object) -> list[Any]:
    if isinstance(raw, list):
        return list(raw)
    return []


def _resolve_config_path(
    raw: str | Path | None,
    *,
    repo_root: Path,
    config_path: Path,
    require_exists: bool = False,
) -> Path | None:
    if raw in (None, ""):
        return None
    candidate = Path(raw)
    if candidate.is_absolute():
        if require_exists and not candidate.exists():
            return None
        return candidate
    probes = [
        (config_path.parent / candidate).resolve(),
        (repo_root / candidate).resolve(),
    ]
    for probe in probes:
        if probe.exists():
            return probe
    if require_exists:
        return None
    return probes[1]


def _default_capability(raw: dict[str, Any]) -> str:
    notes = _as_dict(raw.get("notes"))
    capability = str(raw.get("capability") or notes.get("capability") or "").strip().lower()
    if capability:
        return capability
    dataset_kind = str(raw.get("dataset_kind", "")).strip().lower()
    observation_family = str(raw.get("observation_family") or notes.get("observation_family") or "").strip().lower()
    if "proxy" in dataset_kind or "yield_environment" in observation_family:
        return DatasetCapability.HARVEST_PROXY.value
    if "environment" in dataset_kind or "context" in dataset_kind or "metadata" in dataset_kind:
        return DatasetCapability.CONTEXT_ONLY.value
    return DatasetCapability.MEASURED_HARVEST.value


def _build_dataset_from_config(
    raw: dict[str, Any],
    *,
    repo_root: Path,
    config_path: Path,
) -> DatasetMetadataContract:
    basis_cfg = _as_dict(raw.get("basis"))
    observation_cfg = _as_dict(raw.get("observation"))
    management_cfg = _as_dict(raw.get("management"))
    fixture_cfg = _as_dict(raw.get("sanitized_fixture"))
    notes = _as_dict(raw.get("notes"))
    dataset_id = str(raw["dataset_id"])
    dataset_kind = str(raw.get("dataset_kind", dataset_id))
    display_name = str(raw.get("display_name", dataset_id))
    return DatasetMetadataContract(
        dataset_id=dataset_id,
        dataset_kind=dataset_kind,
        display_name=display_name,
        dataset_family=str(raw.get("dataset_family") or notes.get("dataset_family") or dataset_kind),
        observation_family=str(raw.get("observation_family") or notes.get("observation_family") or ""),
        capability=str(raw.get("capability") or _default_capability(raw)),
        ingestion_status=raw.get("ingestion_status"),
        source_refs=tuple(str(value) for value in _as_list(raw.get("source_refs"))),
        forcing_path=_resolve_config_path(
            raw.get("forcing_path"),
            repo_root=repo_root,
            config_path=config_path,
            require_exists=True,
        ),
        observed_harvest_path=_resolve_config_path(
            raw.get("observed_harvest_path"),
            repo_root=repo_root,
            config_path=config_path,
            require_exists=True,
        ),
        validation_start=raw.get("validation_start"),
        validation_end=raw.get("validation_end"),
        cultivar=str(raw.get("cultivar", "unknown")),
        greenhouse=str(raw.get("greenhouse", "unknown")),
        season=str(raw.get("season", "unknown")),
        basis=DatasetBasisContract(
            reporting_basis=str(basis_cfg.get("reporting_basis", "unknown")),
            plants_per_m2=basis_cfg.get("plants_per_m2"),
        ),
        observation=DatasetObservationContract(
            date_column=observation_cfg.get("date_column"),
            measured_cumulative_column=observation_cfg.get("measured_cumulative_column"),
            estimated_cumulative_column=observation_cfg.get("estimated_cumulative_column"),
            measured_semantics=str(
                observation_cfg.get(
                    "measured_semantics",
                    "cumulative_harvested_fruit_dry_weight_floor_area",
                )
            ),
            daily_increment_column=observation_cfg.get("daily_increment_column"),
        ),
        management=DatasetManagementMetadata(
            pruning_records_path=_resolve_config_path(
                management_cfg.get("pruning_records_path"),
                repo_root=repo_root,
                config_path=config_path,
                require_exists=True,
            ),
            defoliation_records_path=_resolve_config_path(
                management_cfg.get("defoliation_records_path"),
                repo_root=repo_root,
                config_path=config_path,
                require_exists=True,
            ),
            harvest_timing_records_path=_resolve_config_path(
                management_cfg.get("harvest_timing_records_path"),
                repo_root=repo_root,
                config_path=config_path,
                require_exists=True,
            ),
            irrigation_path=_resolve_config_path(
                management_cfg.get("irrigation_path"),
                repo_root=repo_root,
                config_path=config_path,
                require_exists=True,
            ),
            ec_path=_resolve_config_path(
                management_cfg.get("ec_path"),
                repo_root=repo_root,
                config_path=config_path,
                require_exists=True,
            ),
            rootzone_path=_resolve_config_path(
                management_cfg.get("rootzone_path"),
                repo_root=repo_root,
                config_path=config_path,
                require_exists=True,
            ),
        ),
        sanitized_fixture=DatasetSanitizedFixtureContract(
            fixture_kind=str(fixture_cfg.get("fixture_kind", "sanitized_csv_fixture")),
            forcing_fixture_path=_resolve_config_path(
                fixture_cfg.get("forcing_fixture_path"),
                repo_root=repo_root,
                config_path=config_path,
                require_exists=True,
            ),
            observed_harvest_fixture_path=_resolve_config_path(
                fixture_cfg.get("observed_harvest_fixture_path"),
                repo_root=repo_root,
                config_path=config_path,
                require_exists=True,
            ),
        ),
        priority_tags=tuple(str(tag) for tag in _as_list(raw.get("priority_tags"))),
        blocker_codes=tuple(str(code) for code in _as_list(raw.get("blocker_codes"))),
        provenance_tags=tuple(str(tag) for tag in _as_list(raw.get("provenance_tags"))),
        notes=notes,
    )


def _default_knu_dataset(
    *,
    config: dict[str, Any],
    repo_root: Path,
    config_path: Path,
) -> DatasetMetadataContract:
    validation_cfg = _as_dict(config.get("validation"))
    contract = resolve_knu_data_contract(
        validation_cfg=validation_cfg,
        repo_root=repo_root,
        config_path=config_path,
    )
    data = load_knu_validation_data(forcing_path=contract.forcing_path, yield_path=contract.yield_path)
    yield_dates = pd.to_datetime(data.yield_df["Date"], errors="coerce").dropna().dt.normalize()
    return DatasetMetadataContract(
        dataset_id="knu_actual",
        dataset_kind="knu_measured_harvest",
        display_name="KNU measured harvest longrun",
        dataset_family="knu_actual",
        observation_family="yield",
        capability=DatasetCapability.MEASURED_HARVEST,
        ingestion_status=DatasetIngestionStatus.RUNNABLE,
        source_refs=(str(contract.contract_path) if contract.contract_path is not None else "knu_data_contract",),
        forcing_path=contract.forcing_path,
        observed_harvest_path=contract.yield_path,
        validation_start=str(yield_dates.min().date()),
        validation_end=str(yield_dates.max().date()),
        cultivar="unknown",
        greenhouse="KNU",
        season="current_window",
        basis=DatasetBasisContract(
            reporting_basis=contract.reporting_basis,
            plants_per_m2=contract.plants_per_m2,
        ),
        observation=DatasetObservationContract(
            date_column="Date",
            measured_cumulative_column=data.measured_column,
            estimated_cumulative_column=data.estimated_column,
            measured_semantics="cumulative_harvested_fruit_dry_weight_floor_area",
        ),
        management=DatasetManagementMetadata(),
        sanitized_fixture=DatasetSanitizedFixtureContract(
            forcing_fixture_path=(repo_root / "tests" / "fixtures" / "knu_sanitized" / "KNU_Tomato_Env_fixture.csv"),
            observed_harvest_fixture_path=(
                repo_root / "tests" / "fixtures" / "knu_sanitized" / "tomato_validation_data_yield_fixture.csv"
            ),
        ),
        priority_tags=(
            "baseline_window",
            "needs_additional_season",
            "needs_longer_harvest_wave",
            "needs_management_metadata",
            "needs_residence_signal_dataset",
            "prefer_rootzone_metadata",
        ),
        provenance_tags=("actual_data_contract", "knu", "measured_harvest"),
        notes={
            "dataset_source_kind": "actual_data_contract",
            "reporting_basis": contract.reporting_basis,
        },
    )


@dataclass(frozen=True, slots=True)
class DatasetRegistry:
    datasets: tuple[DatasetMetadataContract, ...]
    default_dataset_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        ids = [dataset.dataset_id for dataset in self.datasets]
        if len(ids) != len(set(ids)):
            raise ValueError("Dataset IDs must be unique.")
        missing = [dataset_id for dataset_id in self.default_dataset_ids if dataset_id not in ids]
        if missing:
            raise ValueError(f"default_dataset_ids reference unknown datasets: {missing}")

    def require(self, dataset_id: str) -> DatasetMetadataContract:
        for dataset in self.datasets:
            if dataset.dataset_id == dataset_id:
                return dataset
        raise KeyError(f"Unknown dataset_id {dataset_id!r}")

    def list_by_capability(self, capability: DatasetCapability | str) -> tuple[DatasetMetadataContract, ...]:
        expected = DatasetCapability(str(capability))
        return tuple(dataset for dataset in self.datasets if dataset.capability is expected)

    def runnable_measured_harvest_datasets(self) -> tuple[DatasetMetadataContract, ...]:
        return tuple(dataset for dataset in self.datasets if is_measured_harvest_runnable(dataset))

    def draft_datasets(self) -> tuple[DatasetMetadataContract, ...]:
        return tuple(dataset for dataset in self.datasets if dataset.ingestion_status is not DatasetIngestionStatus.RUNNABLE)

    def to_frame(self) -> pd.DataFrame:
        return dataset_registry_frame(list(self.datasets))

    def blocker_frame(self) -> pd.DataFrame:
        return dataset_blocker_frame(list(self.datasets))

    def to_payload(self) -> dict[str, Any]:
        return {
            "default_dataset_ids": list(self.default_dataset_ids),
            "summary": build_dataset_inventory_summary(list(self.datasets)),
            "datasets": [dataset.to_payload() for dataset in self.datasets],
        }


def _default_dataset_ids(datasets: tuple[DatasetMetadataContract, ...]) -> tuple[str, ...]:
    runnable_ids = tuple(dataset.dataset_id for dataset in datasets if is_measured_harvest_runnable(dataset))
    if runnable_ids:
        return runnable_ids
    return ()


def _merge_dataset_rows(
    imported_rows: list[dict[str, Any]],
    explicit_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    merged: dict[str, dict[str, Any]] = {}
    for row in imported_rows:
        merged[str(row["dataset_id"])] = dict(row)
    for row in explicit_rows:
        dataset_id = str(row["dataset_id"])
        if dataset_id not in merged:
            merged[dataset_id] = dict(row)
            continue
        merged[dataset_id] = _overlay_dataset_row(merged[dataset_id], row)
    return list(merged.values())


def _overlay_dataset_row(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _overlay_dataset_row(_as_dict(merged[key]), value)
        else:
            merged[key] = value
    return merged


def load_dataset_registry_snapshot(
    snapshot_path: str | Path,
    *,
    repo_root: Path,
    config_path: Path,
) -> DatasetRegistry:
    resolved_path = _resolve_config_path(snapshot_path, repo_root=repo_root, config_path=config_path)
    if resolved_path is None:
        raise ValueError("registry snapshot path is required.")
    payload = json.loads(resolved_path.read_text(encoding="utf-8"))
    dataset_rows = [_as_dict(item) for item in _as_list(payload.get("datasets")) if _as_dict(item)]
    datasets = tuple(
        _build_dataset_from_config(row, repo_root=repo_root, config_path=resolved_path)
        for row in dataset_rows
    )
    default_ids = tuple(str(value) for value in _as_list(payload.get("default_dataset_ids")))
    return DatasetRegistry(datasets=datasets, default_dataset_ids=default_ids)


def load_dataset_registry(
    config: dict[str, Any],
    *,
    repo_root: Path,
    config_path: Path,
) -> DatasetRegistry:
    validation_cfg = _as_dict(config.get("validation"))
    datasets_cfg = _as_dict(validation_cfg.get("datasets"))
    imported_rows: list[dict[str, Any]] = []
    snapshot_path = datasets_cfg.get("registry_snapshot_path")
    allow_missing_snapshot = bool(datasets_cfg.get("allow_missing_registry_snapshot", False))
    if snapshot_path not in (None, ""):
        try:
            snapshot_registry = load_dataset_registry_snapshot(
                snapshot_path,
                repo_root=repo_root,
                config_path=config_path,
            )
        except FileNotFoundError:
            if not allow_missing_snapshot:
                raise
        else:
            imported_rows = [dataset.to_payload() for dataset in snapshot_registry.datasets]
    explicit_rows = [_as_dict(item) for item in _as_list(datasets_cfg.get("items")) if _as_dict(item)]
    dataset_rows = _merge_dataset_rows(imported_rows, explicit_rows)
    if dataset_rows:
        datasets = tuple(
            _build_dataset_from_config(row, repo_root=repo_root, config_path=config_path)
            for row in dataset_rows
        )
        explicit_defaults = tuple(str(value) for value in _as_list(datasets_cfg.get("default_dataset_ids")))
        default_ids = explicit_defaults or _default_dataset_ids(datasets)
    else:
        datasets = (_default_knu_dataset(config=config, repo_root=repo_root, config_path=config_path),)
        default_ids = ("knu_actual",)
    return DatasetRegistry(datasets=datasets, default_dataset_ids=default_ids)


__all__ = ["DatasetRegistry", "load_dataset_registry", "load_dataset_registry_snapshot"]
