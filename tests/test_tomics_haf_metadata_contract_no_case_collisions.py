import json

from stomatal_optimiaztion.domains.tomato.tomics.observers.metadata_contract import (
    case_insensitive_duplicate_keys,
    json_has_case_insensitive_duplicate_keys,
    metadata_contract_audit,
    normalize_metadata,
    write_normalized_metadata,
)


def test_metadata_normalizer_removes_power_shell_case_collisions(tmp_path) -> None:
    metadata = {
        "LAI_available": False,
        "lai_available": False,
        "VPD_available": True,
        "vpd_available": True,
        "dataset3_mapping": "direct_loadcell",
        "Dataset3_mapping_confidence": "direct_loadcell_no_date",
        "fruit_diameter_p_values_allowed": False,
        "fruit_diameter_allocation_calibration_target": False,
        "fruit_diameter_model_promotion_target": False,
        "shipped_TOMICS_incumbent_changed": False,
        "shipped_tomics_incumbent_unchanged": True,
    }

    normalized = normalize_metadata(metadata)
    assert case_insensitive_duplicate_keys(normalized) == []
    assert "lai_available" not in normalized
    assert "vpd_available" not in normalized
    assert "dataset3_mapping" not in normalized
    assert normalized["Dataset3_mapping_confidence"] == "direct_loadcell_no_date"
    assert normalized["shipped_TOMICS_incumbent_changed"] is False
    assert normalized["legacy_metadata"]["dataset3_mapping"] == "direct_loadcell"

    metadata_path = write_normalized_metadata(tmp_path / "metadata.json", metadata)
    assert json_has_case_insensitive_duplicate_keys(metadata_path) is False
    written = json.loads(metadata_path.read_text(encoding="utf-8"))
    assert "legacy_metadata" in written


def test_metadata_contract_audit_requires_canonical_top_level_keys() -> None:
    audit = metadata_contract_audit(
        {
            "LAI_available": False,
            "VPD_available": True,
            "Dataset3_mapping_confidence": "direct_loadcell_no_date",
            "fruit_diameter_p_values_allowed": False,
            "fruit_diameter_allocation_calibration_target": False,
            "fruit_diameter_model_promotion_target": False,
            "shipped_TOMICS_incumbent_changed": False,
        }
    )

    assert audit["status"].tolist() == ["pass", "pass"]
