import json

from stomatal_optimiaztion.domains.tomato.tomics.observers.metadata_contract import (
    json_has_case_insensitive_duplicate_keys,
    write_stage_metadata_snapshot,
)


def test_stage_metadata_snapshot_is_normalized_and_keeps_legacy_keys_nested(tmp_path) -> None:
    snapshot = tmp_path / "metadata_goal2_5_production_observer.json"
    write_stage_metadata_snapshot(
        snapshot,
        {
            "LAI_available": False,
            "lai_available": False,
            "VPD_available": True,
            "vpd_available": True,
            "Dataset3_mapping_confidence": "direct_loadcell_no_date",
            "dataset3_mapping": "direct_loadcell",
            "fruit_diameter_p_values_allowed": False,
            "fruit_diameter_allocation_calibration_target": False,
            "fruit_diameter_model_promotion_target": False,
            "shipped_TOMICS_incumbent_changed": False,
        },
    )

    data = json.loads(snapshot.read_text(encoding="utf-8"))
    assert json_has_case_insensitive_duplicate_keys(snapshot) is False
    assert "lai_available" not in data
    assert "vpd_available" not in data
    assert data["legacy_metadata"]["dataset3_mapping"] == "direct_loadcell"
