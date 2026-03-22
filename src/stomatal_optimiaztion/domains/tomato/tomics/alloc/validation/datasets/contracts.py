from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


def _normalize_reporting_basis(value: str) -> str:
    key = str(value).strip().lower()
    if key in {"floor_area", "floor_area_g_m2", "g/m^2", "g m^-2", "g/m2"}:
        return "floor_area_g_m2"
    if key in {"per_plant", "g/plant"}:
        return "g_per_plant"
    raise ValueError(f"Unsupported reporting basis {value!r}.")


@dataclass(frozen=True, slots=True)
class DatasetBasisContract:
    reporting_basis: str
    plants_per_m2: float
    basis_unit_label: str = "g/m^2"

    def __post_init__(self) -> None:
        normalized = _normalize_reporting_basis(self.reporting_basis)
        object.__setattr__(self, "reporting_basis", normalized)
        if float(self.plants_per_m2) <= 0.0:
            raise ValueError("plants_per_m2 must be positive.")
        if normalized == "floor_area_g_m2":
            object.__setattr__(self, "basis_unit_label", "g/m^2")
        elif normalized == "g_per_plant":
            object.__setattr__(self, "basis_unit_label", "g/plant")

    def to_payload(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class DatasetObservationContract:
    date_column: str
    measured_cumulative_column: str
    estimated_cumulative_column: str | None = None
    measured_semantics: str = "cumulative_harvested_fruit_dry_weight_floor_area"
    daily_increment_column: str | None = None

    def __post_init__(self) -> None:
        if not str(self.date_column).strip():
            raise ValueError("date_column is required.")
        if not str(self.measured_cumulative_column).strip():
            raise ValueError("measured_cumulative_column is required.")

    def to_payload(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class DatasetManagementMetadata:
    pruning_records_path: Path | None = None
    defoliation_records_path: Path | None = None
    harvest_timing_records_path: Path | None = None
    irrigation_path: Path | None = None
    ec_path: Path | None = None
    rootzone_path: Path | None = None

    def to_payload(self) -> dict[str, Any]:
        payload = asdict(self)
        for key, value in list(payload.items()):
            payload[key] = str(value) if isinstance(value, Path) else value
        return payload


@dataclass(frozen=True, slots=True)
class DatasetSanitizedFixtureContract:
    fixture_kind: str = "sanitized_csv_fixture"
    forcing_fixture_path: Path | None = None
    observed_harvest_fixture_path: Path | None = None

    def to_payload(self) -> dict[str, Any]:
        payload = asdict(self)
        for key, value in list(payload.items()):
            payload[key] = str(value) if isinstance(value, Path) else value
        return payload


@dataclass(frozen=True, slots=True)
class DatasetMetadataContract:
    dataset_id: str
    dataset_kind: str
    display_name: str
    forcing_path: Path
    observed_harvest_path: Path
    validation_start: str
    validation_end: str
    cultivar: str
    greenhouse: str
    season: str
    basis: DatasetBasisContract
    observation: DatasetObservationContract
    management: DatasetManagementMetadata = field(default_factory=DatasetManagementMetadata)
    sanitized_fixture: DatasetSanitizedFixtureContract = field(default_factory=DatasetSanitizedFixtureContract)
    priority_tags: tuple[str, ...] = ()
    notes: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not str(self.dataset_id).strip():
            raise ValueError("dataset_id is required.")
        if not str(self.dataset_kind).strip():
            raise ValueError("dataset_kind is required.")
        if not str(self.display_name).strip():
            raise ValueError("display_name is required.")
        if not str(self.validation_start).strip() or not str(self.validation_end).strip():
            raise ValueError("validation_start and validation_end are required.")
        object.__setattr__(self, "forcing_path", Path(self.forcing_path))
        object.__setattr__(self, "observed_harvest_path", Path(self.observed_harvest_path))
        object.__setattr__(self, "priority_tags", tuple(str(tag) for tag in self.priority_tags if str(tag).strip()))

    @property
    def has_management_records(self) -> bool:
        return any(
            value is not None
            for value in (
                self.management.pruning_records_path,
                self.management.defoliation_records_path,
                self.management.harvest_timing_records_path,
            )
        )

    def to_payload(self) -> dict[str, Any]:
        return {
            "dataset_id": self.dataset_id,
            "dataset_kind": self.dataset_kind,
            "display_name": self.display_name,
            "forcing_path": str(self.forcing_path),
            "observed_harvest_path": str(self.observed_harvest_path),
            "validation_start": self.validation_start,
            "validation_end": self.validation_end,
            "cultivar": self.cultivar,
            "greenhouse": self.greenhouse,
            "season": self.season,
            "basis": self.basis.to_payload(),
            "observation": self.observation.to_payload(),
            "management": self.management.to_payload(),
            "sanitized_fixture": self.sanitized_fixture.to_payload(),
            "priority_tags": list(self.priority_tags),
            "notes": dict(self.notes),
        }


__all__ = [
    "DatasetBasisContract",
    "DatasetManagementMetadata",
    "DatasetMetadataContract",
    "DatasetObservationContract",
    "DatasetSanitizedFixtureContract",
]
