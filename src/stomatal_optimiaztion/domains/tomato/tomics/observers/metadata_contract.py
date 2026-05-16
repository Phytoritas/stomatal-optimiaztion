from __future__ import annotations

from collections.abc import Mapping
import json
from pathlib import Path
from typing import Any

import pandas as pd

from stomatal_optimiaztion.domains.tomato.tomics.alloc.core import write_json


CANONICAL_TOP_LEVEL_KEYS = {
    "vpd_available": "VPD_available",
    "lai_available": "LAI_available",
    "dataset3_mapping": "Dataset3_mapping_confidence",
    "dataset3_mapping_confidence": "Dataset3_mapping_confidence",
    "shipped_tomics_incumbent_unchanged": "shipped_TOMICS_incumbent_changed",
}
DEPRECATED_TOP_LEVEL_DMC_KEYS = {
    "_".join(("configured", "default", "fruit", "dry", "matter", "content")): (
        "deprecated_previous_default_fruit_DMC_fraction"
    ),
}


def _canonical_key(key: str) -> str:
    return CANONICAL_TOP_LEVEL_KEYS.get(key.casefold(), key)


def normalize_metadata(metadata: Mapping[str, Any]) -> dict[str, Any]:
    """Return metadata with stable top-level keys and no case-insensitive duplicates."""

    normalized: dict[str, Any] = {}
    legacy_metadata: dict[str, Any] = {}
    casefold_to_key: dict[str, str] = {}
    existing_legacy = metadata.get("legacy_metadata")
    if isinstance(existing_legacy, Mapping):
        legacy_metadata.update({str(key): value for key, value in existing_legacy.items()})

    for raw_key, value in metadata.items():
        key = str(raw_key)
        if key == "legacy_metadata":
            continue
        if key.casefold() in DEPRECATED_TOP_LEVEL_DMC_KEYS:
            legacy_key = DEPRECATED_TOP_LEVEL_DMC_KEYS[key.casefold()]
            legacy_metadata[legacy_key] = value
            continue
        canonical = _canonical_key(key)
        canonical_value = value
        if key.casefold() == "shipped_tomics_incumbent_unchanged" and isinstance(value, bool):
            canonical_value = not value
        folded = canonical.casefold()
        if folded in casefold_to_key:
            retained = casefold_to_key[folded]
            if key == canonical:
                normalized[canonical] = canonical_value
                continue
            if key != retained:
                legacy_metadata[key] = value
            continue
        casefold_to_key[folded] = canonical
        normalized[canonical] = canonical_value
        if canonical != key:
            legacy_metadata[key] = value

    if legacy_metadata:
        normalized["legacy_metadata"] = legacy_metadata
    assert_no_case_insensitive_duplicate_keys(normalized)
    return normalized


def case_insensitive_duplicate_keys(metadata: Mapping[str, Any]) -> list[str]:
    seen: dict[str, str] = {}
    duplicates: list[str] = []
    for key in metadata:
        text = str(key)
        folded = text.casefold()
        if folded in seen and seen[folded] != text:
            duplicates.append(text)
        else:
            seen[folded] = text
    return duplicates


def assert_no_case_insensitive_duplicate_keys(metadata: Mapping[str, Any]) -> None:
    duplicates = case_insensitive_duplicate_keys(metadata)
    if duplicates:
        raise ValueError(f"Metadata contains case-insensitive duplicate keys: {duplicates}")


def write_normalized_metadata(path: str | Path, metadata: Mapping[str, Any]) -> Path:
    return write_json(path, normalize_metadata(metadata))


def write_stage_metadata_snapshot(path: str | Path, metadata: Mapping[str, Any]) -> Path:
    return write_normalized_metadata(path, metadata)


def metadata_contract_audit(metadata: Mapping[str, Any]) -> pd.DataFrame:
    normalized = normalize_metadata(metadata)
    rows = [
        {
            "check_name": "no_case_insensitive_duplicate_top_level_keys",
            "status": "pass",
            "violation_count": 0,
            "notes": "Top-level metadata keys are unique under case-insensitive parsers.",
        }
    ]
    required = (
        "LAI_available",
        "VPD_available",
        "Dataset3_mapping_confidence",
        "fruit_diameter_p_values_allowed",
        "fruit_diameter_allocation_calibration_target",
        "fruit_diameter_model_promotion_target",
        "shipped_TOMICS_incumbent_changed",
        "canonical_fruit_DMC_fraction",
        "fruit_DMC_fraction",
        "default_fruit_dry_matter_content",
        "DMC_fixed_for_2025_2C",
        "DMC_sensitivity_enabled",
        "deprecated_previous_default_fruit_DMC_fraction",
    )
    missing = [key for key in required if key not in normalized]
    rows.append(
        {
            "check_name": "canonical_top_level_keys_present",
            "status": "pass" if not missing else "fail",
            "violation_count": len(missing),
            "notes": ";".join(missing),
        }
    )
    return pd.DataFrame(rows)


def json_has_case_insensitive_duplicate_keys(path: str | Path) -> bool:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, Mapping):
        return False
    return bool(case_insensitive_duplicate_keys(data))
