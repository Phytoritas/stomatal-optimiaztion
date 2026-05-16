from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

from stomatal_optimiaztion.domains.tomato.tomics.observers.contracts import (
    RAW_FILENAME_NOTE,
    SEASON_ID,
)

DEFAULT_SENSOR_MAPPING: dict[str, Any] = {
    "season_id": SEASON_ID,
    "raw_filename_note": RAW_FILENAME_NOTE,
    "timestamp_col": "TIMESTAMP",
    "record_col": "RECORD",
    "cadence_minutes": 10,
    "raw_columns": {
        "leaf_temperature_1": "LeafTemp1_Avg",
        "leaf_temperature_2": "LeafTemp2_Avg",
        "fruit_diameter_1": "Fruit1Diameter_Avg",
        "fruit_diameter_2": "Fruit2Diameter_Avg",
        "solar_radiation": "SolarRad_Avg",
    },
    "loadcell_treatment_map": {
        1: "Control",
        2: "Control",
        3: "Control",
        4: "Drought",
        5: "Drought",
        6: "Drought",
    },
    "leaf_sensor_map": {
        "LeafTemp1_Avg": {
            "loadcell_id": 4,
            "treatment": "Drought",
            "mapping_status": "confirmed_by_user",
        },
        "LeafTemp2_Avg": {
            "loadcell_id": 1,
            "treatment": "Control",
            "mapping_status": "confirmed_by_user",
        },
    },
    "fruit_sensor_map": {
        "Fruit1Diameter_Avg": {
            "loadcell_id": 4,
            "treatment": "Drought",
            "mapping_status": "provisional",
        },
        "Fruit2Diameter_Avg": {
            "loadcell_id": 1,
            "treatment": "Control",
            "mapping_status": "provisional",
        },
    },
    "metadata": {
        "biological_replication": False,
        "sensor_level_only": True,
        "fruit_diameter_inference_level": "sensor_level_descriptive_only",
        "fruit_diameter_allowed_use": "apparent_growth_observer",
        "fruit_diameter_disallowed_use": [
            "replicated_treatment_effect_test",
            "p_value_for_treatment_effect",
            "allocation_parameter_calibration",
            "hydraulic_growth_gate_calibration",
            "model_promotion_gate",
        ],
        "leaf_temperature_allowed_use": "paired_leaf_thermal_observer",
        "leaf_mapping_status": "confirmed_by_user",
        "fruit_mapping_status": "provisional",
        "fruit_diameter_p_values_allowed": False,
        "fruit_diameter_allocation_calibration_target": False,
    },
}


def load_sensor_mapping(path: str | Path | None = None) -> dict[str, Any]:
    if path is None:
        return copy.deepcopy(DEFAULT_SENSOR_MAPPING)
    mapping_path = Path(path)
    with mapping_path.open("r", encoding="utf-8") as handle:
        loaded = yaml.safe_load(handle) or {}
    if not isinstance(loaded, dict):
        raise TypeError(f"Sensor mapping must parse to a mapping, got {type(loaded).__name__}.")
    merged = copy.deepcopy(DEFAULT_SENSOR_MAPPING)
    for key, value in loaded.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key].update(value)
        else:
            merged[key] = value
    return merged


def sensor_mapping_rows(mapping: dict[str, Any]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for sensor_type, map_key in (
        ("leaf_temperature", "leaf_sensor_map"),
        ("fruit_diameter", "fruit_sensor_map"),
    ):
        for column, payload in mapping.get(map_key, {}).items():
            rows.append(
                {
                    "sensor_type": sensor_type,
                    "sensor_column": column,
                    "loadcell_id": payload.get("loadcell_id"),
                    "treatment": payload.get("treatment"),
                    "mapping_status": payload.get("mapping_status"),
                    "sensor_level_only": bool(mapping.get("metadata", {}).get("sensor_level_only", True)),
                }
            )
    return pd.DataFrame(rows)


def fruit_diameter_policy_metadata(mapping: dict[str, Any]) -> dict[str, Any]:
    metadata = dict(mapping.get("metadata", {}))
    return {
        "biological_replication": bool(metadata.get("biological_replication", False)),
        "fruit_diameter_sensor_level_only": bool(metadata.get("sensor_level_only", True)),
        "fruit_diameter_treatment_endpoint": False,
        "fruit_diameter_p_values_allowed": bool(metadata.get("fruit_diameter_p_values_allowed", False)),
        "fruit_diameter_allocation_calibration_target": bool(
            metadata.get("fruit_diameter_allocation_calibration_target", False)
        ),
        "fruit_diameter_model_promotion_target": False,
        "fruit_mapping_status": metadata.get("fruit_mapping_status", "provisional"),
        "leaf_mapping_status": metadata.get("leaf_mapping_status", "confirmed_by_user"),
    }

