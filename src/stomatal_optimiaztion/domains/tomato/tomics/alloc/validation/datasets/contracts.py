from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any


class DatasetCapability(str, Enum):
    MEASURED_HARVEST = "measured_harvest"
    HARVEST_PROXY = "harvest_proxy"
    CONTEXT_ONLY = "context_only"


class DatasetIngestionStatus(str, Enum):
    RUNNABLE = "runnable"
    DRAFT_NEEDS_RAW_FIXTURE = "draft_needs_raw_fixture"
    DRAFT_NEEDS_BASIS_METADATA = "draft_needs_basis_metadata"
    DRAFT_NEEDS_HARVEST_MAPPING = "draft_needs_harvest_mapping"
    DRAFT_BLOCKED = "draft_blocked"


RAW_FIXTURE_BLOCKER_CODES = frozenset(
    {
        "missing_raw_fixture",
        "missing_forcing_path",
        "missing_observed_harvest_path",
        "missing_sanitized_fixture",
    }
)
BASIS_BLOCKER_CODES = frozenset({"missing_reporting_basis", "missing_plants_per_m2"})
HARVEST_MAPPING_BLOCKER_CODES = frozenset(
    {
        "missing_validation_window",
        "missing_date_column",
        "missing_measured_cumulative_column",
        "ambiguous_harvest_semantics",
        "review_only_dry_matter_conversion",
    }
)


def _normalize_optional_text(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text if text else None


def _normalize_reporting_basis(value: str | None) -> str:
    key = str(value or "").strip().lower()
    if key in {"", "unknown", "na", "n/a"}:
        return "unknown"
    if key in {"floor_area", "floor_area_g_m2", "g/m^2", "g m^-2", "g/m2"}:
        return "floor_area_g_m2"
    if key in {"per_plant", "g/plant"}:
        return "g_per_plant"
    raise ValueError(f"Unsupported reporting basis {value!r}.")


def _normalize_capability(value: DatasetCapability | str | None) -> DatasetCapability:
    if isinstance(value, DatasetCapability):
        return value
    key = str(value or DatasetCapability.MEASURED_HARVEST.value).strip().lower()
    return DatasetCapability(key)


def _normalize_ingestion_status(value: DatasetIngestionStatus | str | None) -> DatasetIngestionStatus | None:
    if value is None:
        return None
    if isinstance(value, DatasetIngestionStatus):
        return value
    return DatasetIngestionStatus(str(value).strip().lower())


@dataclass(frozen=True, slots=True)
class DatasetBasisContract:
    reporting_basis: str = "unknown"
    plants_per_m2: float | None = None
    basis_unit_label: str = "unknown"

    def __post_init__(self) -> None:
        normalized = _normalize_reporting_basis(self.reporting_basis)
        object.__setattr__(self, "reporting_basis", normalized)
        plants_per_m2 = None if self.plants_per_m2 in (None, "") else float(self.plants_per_m2)
        if plants_per_m2 is not None and plants_per_m2 <= 0.0:
            raise ValueError("plants_per_m2 must be positive when provided.")
        if normalized == "g_per_plant" and plants_per_m2 is None:
            raise ValueError("plants_per_m2 is required for per-plant reporting.")
        object.__setattr__(self, "plants_per_m2", plants_per_m2)
        if normalized == "floor_area_g_m2":
            object.__setattr__(self, "basis_unit_label", "g/m^2")
        elif normalized == "g_per_plant":
            object.__setattr__(self, "basis_unit_label", "g/plant")
        else:
            object.__setattr__(self, "basis_unit_label", "unknown")

    @property
    def requires_plant_density(self) -> bool:
        return self.reporting_basis == "g_per_plant"

    @property
    def normalization_resolved(self) -> bool:
        return self.reporting_basis == "floor_area_g_m2" or (
            self.reporting_basis == "g_per_plant" and self.plants_per_m2 is not None
        )

    def to_payload(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class DatasetObservationContract:
    date_column: str | None = None
    measured_cumulative_column: str | None = None
    estimated_cumulative_column: str | None = None
    measured_semantics: str = "cumulative_harvested_fruit_dry_weight_floor_area"
    daily_increment_column: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "date_column", _normalize_optional_text(self.date_column))
        object.__setattr__(
            self,
            "measured_cumulative_column",
            _normalize_optional_text(self.measured_cumulative_column),
        )
        object.__setattr__(
            self,
            "estimated_cumulative_column",
            _normalize_optional_text(self.estimated_cumulative_column),
        )
        object.__setattr__(self, "daily_increment_column", _normalize_optional_text(self.daily_increment_column))
        object.__setattr__(self, "measured_semantics", str(self.measured_semantics or "").strip())

    @property
    def has_explicit_cumulative_mapping(self) -> bool:
        return self.date_column is not None and self.measured_cumulative_column is not None

    def to_payload(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class DatasetDryMatterConversionContract:
    mode: str = "none"
    fresh_weight_column: str | None = None
    dry_matter_ratio: float | None = None
    dry_matter_ratio_low: float | None = None
    dry_matter_ratio_high: float | None = None
    citations: tuple[str, ...] = ()
    review_only: bool = True

    def __post_init__(self) -> None:
        mode = str(self.mode or "none").strip().lower()
        if mode in {"", "disabled"}:
            mode = "none"
        object.__setattr__(self, "mode", mode)
        object.__setattr__(self, "fresh_weight_column", _normalize_optional_text(self.fresh_weight_column))
        ratio = None if self.dry_matter_ratio in (None, "") else float(self.dry_matter_ratio)
        ratio_low = None if self.dry_matter_ratio_low in (None, "") else float(self.dry_matter_ratio_low)
        ratio_high = None if self.dry_matter_ratio_high in (None, "") else float(self.dry_matter_ratio_high)
        for value, label in (
            (ratio, "dry_matter_ratio"),
            (ratio_low, "dry_matter_ratio_low"),
            (ratio_high, "dry_matter_ratio_high"),
        ):
            if value is not None and not (0.0 < value < 1.0):
                raise ValueError(f"{label} must be between 0 and 1 when provided.")
        if ratio_low is not None and ratio_high is not None and ratio_low > ratio_high:
            raise ValueError("dry_matter_ratio_low cannot exceed dry_matter_ratio_high.")
        if ratio is not None and ratio_low is not None and ratio < ratio_low:
            raise ValueError("dry_matter_ratio cannot be lower than dry_matter_ratio_low.")
        if ratio is not None and ratio_high is not None and ratio > ratio_high:
            raise ValueError("dry_matter_ratio cannot exceed dry_matter_ratio_high.")
        object.__setattr__(self, "dry_matter_ratio", ratio)
        object.__setattr__(self, "dry_matter_ratio_low", ratio_low)
        object.__setattr__(self, "dry_matter_ratio_high", ratio_high)
        object.__setattr__(
            self,
            "citations",
            tuple(str(citation) for citation in self.citations if str(citation).strip()),
        )
        object.__setattr__(self, "review_only", bool(self.review_only))
        if self.mode != "none" and self.dry_matter_ratio is None:
            raise ValueError("dry_matter_ratio is required when dry-matter conversion mode is enabled.")

    @property
    def enabled(self) -> bool:
        return self.mode != "none" and self.dry_matter_ratio is not None

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

    def __post_init__(self) -> None:
        for field_name in (
            "pruning_records_path",
            "defoliation_records_path",
            "harvest_timing_records_path",
            "irrigation_path",
            "ec_path",
            "rootzone_path",
        ):
            raw = getattr(self, field_name)
            object.__setattr__(self, field_name, Path(raw) if raw not in (None, "") else None)

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

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "forcing_fixture_path",
            Path(self.forcing_fixture_path) if self.forcing_fixture_path not in (None, "") else None,
        )
        object.__setattr__(
            self,
            "observed_harvest_fixture_path",
            Path(self.observed_harvest_fixture_path) if self.observed_harvest_fixture_path not in (None, "") else None,
        )

    @property
    def is_complete(self) -> bool:
        return self.forcing_fixture_path is not None and self.observed_harvest_fixture_path is not None

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
    forcing_path: Path | None = None
    observed_harvest_path: Path | None = None
    validation_start: str | None = None
    validation_end: str | None = None
    cultivar: str = "unknown"
    greenhouse: str = "unknown"
    season: str = "unknown"
    dataset_family: str = ""
    observation_family: str = ""
    capability: DatasetCapability | str | None = None
    ingestion_status: DatasetIngestionStatus | str | None = None
    source_refs: tuple[str, ...] = ()
    basis: DatasetBasisContract = field(default_factory=DatasetBasisContract)
    observation: DatasetObservationContract = field(default_factory=DatasetObservationContract)
    dry_matter_conversion: DatasetDryMatterConversionContract = field(
        default_factory=DatasetDryMatterConversionContract
    )
    management: DatasetManagementMetadata = field(default_factory=DatasetManagementMetadata)
    sanitized_fixture: DatasetSanitizedFixtureContract = field(default_factory=DatasetSanitizedFixtureContract)
    priority_tags: tuple[str, ...] = ()
    blocker_codes: tuple[str, ...] = ()
    provenance_tags: tuple[str, ...] = ()
    notes: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not str(self.dataset_id).strip():
            raise ValueError("dataset_id is required.")
        if not str(self.dataset_kind).strip():
            raise ValueError("dataset_kind is required.")
        if not str(self.display_name).strip():
            raise ValueError("display_name is required.")

        forcing_path = Path(self.forcing_path) if self.forcing_path not in (None, "") else None
        observed_harvest_path = (
            Path(self.observed_harvest_path) if self.observed_harvest_path not in (None, "") else None
        )
        object.__setattr__(self, "forcing_path", forcing_path)
        object.__setattr__(self, "observed_harvest_path", observed_harvest_path)
        object.__setattr__(self, "validation_start", _normalize_optional_text(self.validation_start))
        object.__setattr__(self, "validation_end", _normalize_optional_text(self.validation_end))
        object.__setattr__(self, "dataset_family", str(self.dataset_family or "").strip())
        object.__setattr__(self, "observation_family", str(self.observation_family or "").strip())
        object.__setattr__(self, "capability", _normalize_capability(self.capability))
        object.__setattr__(
            self,
            "priority_tags",
            tuple(str(tag) for tag in self.priority_tags if str(tag).strip()),
        )
        object.__setattr__(
            self,
            "source_refs",
            tuple(str(ref) for ref in self.source_refs if str(ref).strip()),
        )
        object.__setattr__(
            self,
            "provenance_tags",
            tuple(str(tag) for tag in self.provenance_tags if str(tag).strip()),
        )
        explicit_blockers = tuple(str(code) for code in self.blocker_codes if str(code).strip())
        derived_blockers = tuple(classify_blockers(self))
        merged_blockers = tuple(sorted(set(explicit_blockers) | set(derived_blockers)))
        object.__setattr__(self, "blocker_codes", merged_blockers)
        normalized_status = _normalize_ingestion_status(self.ingestion_status)
        if normalized_status is None:
            normalized_status = derive_ingestion_status(self.capability, merged_blockers)
        object.__setattr__(self, "ingestion_status", normalized_status)

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

    @property
    def sanitized_fixture_path(self) -> Path | None:
        if self.sanitized_fixture.is_complete:
            return self.sanitized_fixture.forcing_fixture_path.parent
        return None

    @property
    def is_runnable_measured_harvest(self) -> bool:
        return is_measured_harvest_runnable(self)

    def to_payload(self) -> dict[str, Any]:
        return {
            "dataset_id": self.dataset_id,
            "dataset_kind": self.dataset_kind,
            "display_name": self.display_name,
            "dataset_family": self.dataset_family,
            "observation_family": self.observation_family,
            "capability": self.capability.value,
            "ingestion_status": self.ingestion_status.value,
            "source_refs": list(self.source_refs),
            "forcing_path": str(self.forcing_path) if self.forcing_path is not None else None,
            "observed_harvest_path": (
                str(self.observed_harvest_path) if self.observed_harvest_path is not None else None
            ),
            "validation_start": self.validation_start,
            "validation_end": self.validation_end,
            "cultivar": self.cultivar,
            "greenhouse": self.greenhouse,
            "season": self.season,
            "basis": self.basis.to_payload(),
            "observation": self.observation.to_payload(),
            "dry_matter_conversion": self.dry_matter_conversion.to_payload(),
            "management": self.management.to_payload(),
            "sanitized_fixture": self.sanitized_fixture.to_payload(),
            "sanitized_fixture_path": (
                str(self.sanitized_fixture_path) if self.sanitized_fixture_path is not None else None
            ),
            "priority_tags": list(self.priority_tags),
            "blocker_codes": list(self.blocker_codes),
            "provenance_tags": list(self.provenance_tags),
            "notes": dict(self.notes),
        }


def missing_required_fields(dataset: DatasetMetadataContract) -> list[str]:
    missing: list[str] = []
    if dataset.forcing_path is None:
        missing.append("forcing_path")
    if dataset.capability is DatasetCapability.MEASURED_HARVEST and dataset.observed_harvest_path is None:
        missing.append("observed_harvest_path")
    if dataset.capability is DatasetCapability.MEASURED_HARVEST and not dataset.validation_start:
        missing.append("validation_start")
    if dataset.capability is DatasetCapability.MEASURED_HARVEST and not dataset.validation_end:
        missing.append("validation_end")
    if dataset.capability is DatasetCapability.MEASURED_HARVEST and dataset.basis.reporting_basis == "unknown":
        missing.append("reporting_basis")
    if dataset.capability is DatasetCapability.MEASURED_HARVEST and dataset.basis.requires_plant_density:
        if dataset.basis.plants_per_m2 is None:
            missing.append("plants_per_m2")
    if dataset.capability is DatasetCapability.MEASURED_HARVEST and dataset.observation.date_column is None:
        missing.append("date_column")
    if dataset.capability is DatasetCapability.MEASURED_HARVEST and dataset.observation.measured_cumulative_column is None:
        missing.append("measured_cumulative_column")
    if dataset.capability is DatasetCapability.MEASURED_HARVEST and not dataset.sanitized_fixture.is_complete:
        missing.append("sanitized_fixture")
    return missing


def classify_blockers(dataset: DatasetMetadataContract) -> list[str]:
    blockers: list[str] = []
    if dataset.forcing_path is None and dataset.observed_harvest_path is None and not dataset.sanitized_fixture.is_complete:
        blockers.append("missing_raw_fixture")
    elif dataset.forcing_path is None:
        blockers.append("missing_forcing_path")
    if dataset.capability is DatasetCapability.MEASURED_HARVEST:
        if dataset.observed_harvest_path is None:
            blockers.append("missing_observed_harvest_path")
        if dataset.basis.reporting_basis == "unknown":
            blockers.append("missing_reporting_basis")
        if dataset.basis.requires_plant_density and dataset.basis.plants_per_m2 is None:
            blockers.append("missing_plants_per_m2")
        if not dataset.validation_start or not dataset.validation_end:
            blockers.append("missing_validation_window")
        if dataset.observation.date_column is None:
            blockers.append("missing_date_column")
        if dataset.observation.measured_cumulative_column is None:
            blockers.append("missing_measured_cumulative_column")
        semantics = dataset.observation.measured_semantics.strip().lower()
        if dataset.dry_matter_conversion.enabled and dataset.dry_matter_conversion.review_only:
            blockers.append("review_only_dry_matter_conversion")
        elif "cumulative_harvested" not in semantics:
            blockers.append("ambiguous_harvest_semantics")
        if not dataset.sanitized_fixture.is_complete:
            blockers.append("missing_sanitized_fixture")
    return sorted(set(blockers))


def derive_ingestion_status(
    capability: DatasetCapability | str,
    blocker_codes: list[str] | tuple[str, ...],
) -> DatasetIngestionStatus:
    del capability
    blocker_set = {str(code) for code in blocker_codes if str(code).strip()}
    if not blocker_set:
        return DatasetIngestionStatus.RUNNABLE
    if blocker_set & RAW_FIXTURE_BLOCKER_CODES:
        return DatasetIngestionStatus.DRAFT_NEEDS_RAW_FIXTURE
    if blocker_set & BASIS_BLOCKER_CODES:
        return DatasetIngestionStatus.DRAFT_NEEDS_BASIS_METADATA
    if blocker_set & HARVEST_MAPPING_BLOCKER_CODES:
        return DatasetIngestionStatus.DRAFT_NEEDS_HARVEST_MAPPING
    return DatasetIngestionStatus.DRAFT_BLOCKED


def infer_ingestion_status(
    *,
    capability: DatasetCapability | str,
    blocker_codes: list[str] | tuple[str, ...],
    has_source_refs: bool | None = None,
) -> DatasetIngestionStatus:
    del has_source_refs
    return derive_ingestion_status(capability, blocker_codes)


def is_measured_harvest_runnable(dataset: DatasetMetadataContract) -> bool:
    if dataset.capability is not DatasetCapability.MEASURED_HARVEST:
        return False
    if dataset.ingestion_status is not DatasetIngestionStatus.RUNNABLE:
        return False
    if dataset.dry_matter_conversion.enabled and dataset.dry_matter_conversion.review_only:
        return False
    if classify_blockers(dataset):
        return False
    semantics = dataset.observation.measured_semantics.strip().lower()
    return (
        dataset.forcing_path is not None
        and dataset.observed_harvest_path is not None
        and dataset.validation_start is not None
        and dataset.validation_end is not None
        and dataset.observation.has_explicit_cumulative_mapping
        and dataset.basis.normalization_resolved
        and "cumulative_harvested" in semantics
        and dataset.sanitized_fixture.is_complete
    )


__all__ = [
    "DatasetBasisContract",
    "DatasetCapability",
    "DatasetDryMatterConversionContract",
    "DatasetIngestionStatus",
    "DatasetManagementMetadata",
    "DatasetMetadataContract",
    "DatasetObservationContract",
    "DatasetSanitizedFixtureContract",
    "classify_blockers",
    "derive_ingestion_status",
    "infer_ingestion_status",
    "is_measured_harvest_runnable",
    "missing_required_fields",
]
