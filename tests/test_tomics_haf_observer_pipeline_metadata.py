from pathlib import Path

import pandas as pd
import yaml

from stomatal_optimiaztion.domains.tomato.tomics.observers.pipeline import (
    run_tomics_haf_observer_pipeline,
)


def _write_toa5(path: Path) -> None:
    path.write_text(
        "\n".join(
            [
                '"TOA5","station","CR1000"',
                '"TIMESTAMP","RECORD","SolarRad_Avg","LeafTemp1_Avg","LeafTemp2_Avg","Fruit1Diameter_Avg","Fruit2Diameter_Avg"',
                '"TS","RN","W/m2","Deg C","Deg C","mm","mm"',
                '"","","Avg","Avg","Avg","Avg","Avg"',
                '"2025-12-14 06:00:00",1,0,24.0,23.0,30.0,31.0',
                '"2025-12-14 06:10:00",2,20,24.5,23.5,30.2,31.1',
                '"2025-12-14 18:00:00",3,0,22.0,21.0,30.4,31.2',
                '"2025-12-15 06:00:00",4,10,23.0,22.0,30.7,31.3',
            ]
        ),
        encoding="utf-8",
    )


def test_observer_pipeline_metadata_contract(tmp_path: Path) -> None:
    raw_root = tmp_path / "raw"
    raw_root.mkdir()
    _write_toa5(raw_root / "sensor.dat")

    dataset1 = pd.DataFrame(
        {
            "timestamp": pd.to_datetime(
                [
                    "2025-12-14 06:00",
                    "2025-12-14 06:10",
                    "2025-12-14 18:00",
                    "2025-12-14 18:10",
                    "2025-12-14 06:00",
                    "2025-12-14 06:10",
                    "2025-12-14 18:00",
                    "2025-12-14 18:10",
                ]
            ),
            "date": ["2025-12-14"] * 8,
            "loadcell_id": [1, 1, 1, 1, 4, 4, 4, 4],
            "sample_id": [1, 1, 1, 1, 4, 4, 4, 4],
            "treatment": ["Control"] * 4 + ["Drought"] * 4,
            "loadcell_weight_kg": [10.0, 9.99, 9.98, 9.97, 9.0, 8.99, 8.98, 8.97],
            "env_inside_radiation_wm2": [10.0, 20.0, 0.0, 0.0, 10.0, 20.0, 0.0, 0.0],
            "env_vpd_kpa": [2.0] * 8,
            "env_air_temperature_c": [25.0] * 8,
            "env_co2_ppm": [400.0] * 8,
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
            "loadcell_weight_kg": [10.0, 9.0],
            "moisture_percent": [80.0, 40.0],
            "ec_ds": [2.0, 3.0],
            "tensiometer_hp": [1.0, 2.0],
        }
    )
    dataset2.to_parquet(raw_root / "dataset2.parquet", index=False)

    dataset3 = pd.DataFrame(
        {
            "season": ["2025_2C"],
            "sample_id": [1],
            "loadcell_id": [1],
            "treatment": ["Control"],
            "flowering_date": ["2025-12-14"],
            "stem_diameter": [9.0],
            "flower_cluster_height": [120.0],
        }
    )
    dataset3.to_parquet(raw_root / "dataset3.parquet", index=False)

    mapping_path = tmp_path / "mapping.yaml"
    mapping_path.write_text(
        yaml.safe_dump(
            {
                "timestamp_col": "TIMESTAMP",
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
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        yaml.safe_dump(
            {
                "paths": {"repo_root": str(tmp_path)},
                "tomics_haf": {
                    "raw_data_root": "raw",
                    "output_root": "out",
                    "sensor_mapping_path": str(mapping_path),
                    "input_files": {
                        "fruit_leaf_temperature_solar_raw_dat": "sensor.dat",
                        "dataset1": "dataset1.parquet",
                        "dataset2": "dataset2.parquet",
                        "dataset3": "dataset3.parquet",
                    },
                },
                "observer_pipeline": {
                    "parquet_batch_size": 10,
                    "max_full_rows_without_limit": 1000,
                    "max_rows": {"dataset1": None, "dataset2": None, "dataset3": None},
                },
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    result = run_tomics_haf_observer_pipeline(config_path)
    metadata = result["metadata"]

    assert metadata["season_id"] == "2025_2C"
    assert metadata["radiation_column_used"] == "env_inside_radiation_wm2"
    assert metadata["dataset1_radiation_directly_usable"] is True
    assert metadata["fallback_required"] is False
    assert metadata["fixed_clock_daynight_primary"] is False
    assert metadata["radiation_thresholds_tested"] == [0, 1, 5, 10]
    assert metadata["latent_allocation_inference_run"] is False
    assert metadata["harvest_family_factorial_run"] is False
    assert metadata["promotion_gate_run"] is False
    assert metadata["shipped_TOMICS_incumbent_changed"] is False
    assert Path(result["outputs"]["observer_feature_frame"]).exists()
