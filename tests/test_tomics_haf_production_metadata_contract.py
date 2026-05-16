from pathlib import Path

import pandas as pd
import yaml

from stomatal_optimiaztion.domains.tomato.tomics.observers.pipeline import (
    run_tomics_haf_observer_pipeline,
)


def _write_raw_dat(path: Path) -> None:
    path.write_text(
        "\n".join(
            [
                '"TOA5","station","CR1000"',
                '"TIMESTAMP","RECORD","SolarRad_Avg","LeafTemp1_Avg","LeafTemp2_Avg","Fruit1Diameter_Avg","Fruit2Diameter_Avg"',
                '"TS","RN","W/m2","Deg C","Deg C","mm","mm"',
                '"","","Avg","Avg","Avg","Avg","Avg"',
                '"2025-12-14 06:00:00",1,10,24.0,23.0,30.0,31.0',
                '"2025-12-14 18:00:00",2,0,22.0,21.0,30.4,31.2',
                '"2025-12-15 06:00:00",3,10,23.0,22.0,30.7,31.3',
            ]
        ),
        encoding="utf-8",
    )


def _write_inputs(raw_root: Path) -> None:
    raw_root.mkdir()
    _write_raw_dat(raw_root / "sensor.dat")
    dataset1 = pd.DataFrame(
        {
            "timestamp": pd.to_datetime(
                [
                    "2025-12-14 06:00",
                    "2025-12-14 06:10",
                    "2025-12-14 18:00",
                    "2025-12-14 18:10",
                ]
            ),
            "date": ["2025-12-14"] * 4,
            "loadcell_id": [1, 1, 4, 4],
            "sample_id": [1, 1, 4, 4],
            "treatment": ["Control", "Control", "Drought", "Drought"],
            "loadcell_weight_kg": [10.0, 9.99, 9.0, 8.99],
            "env_inside_radiation_wm2": [10.0, 20.0, 0.0, 0.0],
            "env_vpd_kpa": [2.0] * 4,
            "env_air_temperature_c": [25.0] * 4,
            "env_co2_ppm": [400.0] * 4,
        }
    )
    dataset1.to_parquet(raw_root / "dataset1.parquet", index=False)
    dataset2 = pd.DataFrame(
        {
            "timestamp": pd.to_datetime(["2025-12-14 00:00", "2025-12-14 00:00"]),
            "date": ["2025-12-14", "2025-12-14"],
            "loadcell_id": [1, 4],
            "sample_id": [1, 4],
            "treatment": ["Control", "Drought"],
            "moisture_percent": [80.0, 40.0],
            "ec_ds": [2.0, 3.0],
            "tensiometer_hp": [1.0, 2.0],
        }
    )
    dataset2.to_parquet(raw_root / "dataset2.parquet", index=False)
    pd.DataFrame({"loadcell_id": [1], "treatment": ["Control"], "stem_diameter": [9.0]}).to_parquet(
        raw_root / "dataset3.parquet",
        index=False,
    )


def _write_mapping(path: Path) -> None:
    path.write_text(
        yaml.safe_dump(
            {
                "timestamp_col": "TIMESTAMP",
                "leaf_sensor_map": {
                    "LeafTemp1_Avg": {"loadcell_id": 4, "treatment": "Drought", "mapping_status": "confirmed_by_user"},
                    "LeafTemp2_Avg": {"loadcell_id": 1, "treatment": "Control", "mapping_status": "confirmed_by_user"},
                },
                "fruit_sensor_map": {
                    "Fruit1Diameter_Avg": {"loadcell_id": 4, "treatment": "Drought", "mapping_status": "provisional"},
                    "Fruit2Diameter_Avg": {"loadcell_id": 1, "treatment": "Control", "mapping_status": "provisional"},
                },
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )


def _write_config(tmp_path: Path, *, mode: str, output_root: str, dataset1_cap: int | None) -> Path:
    config_path = tmp_path / f"{mode}.yaml"
    config_path.write_text(
        yaml.safe_dump(
            {
                "paths": {"repo_root": str(tmp_path)},
                "tomics_haf": {
                    "raw_data_root": "raw",
                    "output_root": output_root,
                    "sensor_mapping_path": str(tmp_path / "mapping.yaml"),
                    "input_files": {
                        "fruit_leaf_temperature_solar_raw_dat": "sensor.dat",
                        "dataset1": "dataset1.parquet",
                        "dataset2": "dataset2.parquet",
                        "dataset3": "dataset3.parquet",
                    },
                },
                "observer_pipeline": {
                    "mode": mode,
                    "parquet_batch_size": 2,
                    "max_full_rows_without_limit": 1000,
                    "max_rows": {
                        "dataset1": dataset1_cap,
                        "dataset2": None,
                        "dataset3": None,
                    },
                    "write_intermediate_chunk_manifests": mode == "production",
                },
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    return config_path


def test_production_and_smoke_metadata_contracts(tmp_path: Path) -> None:
    _write_inputs(tmp_path / "raw")
    _write_mapping(tmp_path / "mapping.yaml")

    production = run_tomics_haf_observer_pipeline(
        _write_config(tmp_path, mode="production", output_root="out_production", dataset1_cap=None)
    )["metadata"]
    smoke = run_tomics_haf_observer_pipeline(
        _write_config(tmp_path, mode="smoke", output_root="out_smoke", dataset1_cap=2)
    )["metadata"]

    assert production["observer_pipeline_mode"] == "production"
    assert production["chunk_aggregation_used"] is True
    assert production["row_cap_applied"] is False
    assert production["dataset1_rows_processed_fraction"] == 1.0
    assert production["dataset2_rows_processed_fraction"] == 1.0
    assert production["production_ready_for_latent_allocation"] is True
    assert production["latent_allocation_inference_run"] is False
    assert production["harvest_family_factorial_run"] is False
    assert production["promotion_gate_run"] is False
    assert production["shipped_TOMICS_incumbent_changed"] is False
    assert production["fruit_diameter_p_values_allowed"] is False
    assert production["fruit_diameter_allocation_calibration_target"] is False
    assert production["fruit_diameter_model_promotion_target"] is False
    assert production["canonical_fruit_DMC_fraction"] == 0.056
    assert production["fruit_DMC_fraction"] == 0.056
    assert production["default_fruit_dry_matter_content"] == 0.056
    assert production["DMC_fixed_for_2025_2C"] is True
    assert production["DMC_sensitivity_enabled"] is False
    assert production["DMC_sensitivity_values"] == []
    assert production["deprecated_previous_default_fruit_DMC_fraction"] == 0.065

    assert smoke["observer_pipeline_mode"] == "smoke"
    assert smoke["row_cap_applied"] is True
    assert smoke["production_ready_for_latent_allocation"] is False
