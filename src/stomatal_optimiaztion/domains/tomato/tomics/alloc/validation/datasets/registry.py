from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.data_contract import (
    resolve_knu_data_contract,
)
from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.datasets.contracts import (
    DatasetBasisContract,
    DatasetManagementMetadata,
    DatasetMetadataContract,
    DatasetObservationContract,
    DatasetSanitizedFixtureContract,
)
from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.datasets.metadata import (
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


def _resolve_config_path(raw: str | Path, *, repo_root: Path, config_path: Path) -> Path:
    candidate = Path(raw)
    if candidate.is_absolute():
        return candidate
    probes = [
        (config_path.parent / candidate).resolve(),
        (repo_root / candidate).resolve(),
    ]
    for probe in probes:
        if probe.exists():
            return probe
    return probes[1]


def _optional_path(raw: object, *, repo_root: Path, config_path: Path) -> Path | None:
    if raw in (None, ""):
        return None
    return _resolve_config_path(str(raw), repo_root=repo_root, config_path=config_path)


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
    return DatasetMetadataContract(
        dataset_id=str(raw["dataset_id"]),
        dataset_kind=str(raw.get("dataset_kind", raw["dataset_id"])),
        display_name=str(raw.get("display_name", raw["dataset_id"])),
        forcing_path=_resolve_config_path(str(raw["forcing_path"]), repo_root=repo_root, config_path=config_path),
        observed_harvest_path=_resolve_config_path(
            str(raw["observed_harvest_path"]),
            repo_root=repo_root,
            config_path=config_path,
        ),
        validation_start=str(raw["validation_start"]),
        validation_end=str(raw["validation_end"]),
        cultivar=str(raw.get("cultivar", "unknown")),
        greenhouse=str(raw.get("greenhouse", "unknown")),
        season=str(raw.get("season", "unknown")),
        basis=DatasetBasisContract(
            reporting_basis=str(basis_cfg.get("reporting_basis", "floor_area_g_m2")),
            plants_per_m2=float(basis_cfg.get("plants_per_m2", 1.0)),
        ),
        observation=DatasetObservationContract(
            date_column=str(observation_cfg.get("date_column", "date")),
            measured_cumulative_column=str(
                observation_cfg.get("measured_cumulative_column", "measured_cumulative_total_fruit_dry_weight_floor_area")
            ),
            estimated_cumulative_column=(
                str(observation_cfg["estimated_cumulative_column"])
                if observation_cfg.get("estimated_cumulative_column") is not None
                else None
            ),
            measured_semantics=str(
                observation_cfg.get(
                    "measured_semantics",
                    "cumulative_harvested_fruit_dry_weight_floor_area",
                )
            ),
            daily_increment_column=(
                str(observation_cfg["daily_increment_column"])
                if observation_cfg.get("daily_increment_column") is not None
                else None
            ),
        ),
        management=DatasetManagementMetadata(
            pruning_records_path=_optional_path(management_cfg.get("pruning_records_path"), repo_root=repo_root, config_path=config_path),
            defoliation_records_path=_optional_path(
                management_cfg.get("defoliation_records_path"),
                repo_root=repo_root,
                config_path=config_path,
            ),
            harvest_timing_records_path=_optional_path(
                management_cfg.get("harvest_timing_records_path"),
                repo_root=repo_root,
                config_path=config_path,
            ),
            irrigation_path=_optional_path(management_cfg.get("irrigation_path"), repo_root=repo_root, config_path=config_path),
            ec_path=_optional_path(management_cfg.get("ec_path"), repo_root=repo_root, config_path=config_path),
            rootzone_path=_optional_path(management_cfg.get("rootzone_path"), repo_root=repo_root, config_path=config_path),
        ),
        sanitized_fixture=DatasetSanitizedFixtureContract(
            fixture_kind=str(fixture_cfg.get("fixture_kind", "sanitized_csv_fixture")),
            forcing_fixture_path=_optional_path(fixture_cfg.get("forcing_fixture_path"), repo_root=repo_root, config_path=config_path),
            observed_harvest_fixture_path=_optional_path(
                fixture_cfg.get("observed_harvest_fixture_path"),
                repo_root=repo_root,
                config_path=config_path,
            ),
        ),
        priority_tags=tuple(str(tag) for tag in _as_list(raw.get("priority_tags"))),
        notes=_as_dict(raw.get("notes")),
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
        if not self.default_dataset_ids:
            raise ValueError("At least one default dataset_id is required.")
        missing = [dataset_id for dataset_id in self.default_dataset_ids if dataset_id not in ids]
        if missing:
            raise ValueError(f"default_dataset_ids reference unknown datasets: {missing}")

    def require(self, dataset_id: str) -> DatasetMetadataContract:
        for dataset in self.datasets:
            if dataset.dataset_id == dataset_id:
                return dataset
        raise KeyError(f"Unknown dataset_id {dataset_id!r}")

    def to_frame(self) -> pd.DataFrame:
        return dataset_registry_frame(list(self.datasets))

    def to_payload(self) -> dict[str, Any]:
        return {
            "default_dataset_ids": list(self.default_dataset_ids),
            "datasets": [dataset.to_payload() for dataset in self.datasets],
        }


def load_dataset_registry(
    config: dict[str, Any],
    *,
    repo_root: Path,
    config_path: Path,
) -> DatasetRegistry:
    validation_cfg = _as_dict(config.get("validation"))
    datasets_cfg = _as_dict(validation_cfg.get("datasets"))
    dataset_rows = [_as_dict(item) for item in _as_list(datasets_cfg.get("items")) if _as_dict(item)]
    if dataset_rows:
        datasets = tuple(
            _build_dataset_from_config(row, repo_root=repo_root, config_path=config_path)
            for row in dataset_rows
        )
        default_ids = tuple(str(value) for value in _as_list(datasets_cfg.get("default_dataset_ids")))
    else:
        datasets = (_default_knu_dataset(config=config, repo_root=repo_root, config_path=config_path),)
        default_ids = ("knu_actual",)
    return DatasetRegistry(datasets=datasets, default_dataset_ids=default_ids)


__all__ = ["DatasetRegistry", "load_dataset_registry"]
