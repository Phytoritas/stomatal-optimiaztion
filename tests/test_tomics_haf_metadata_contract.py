from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from stomatal_optimiaztion.domains.tomato.tomics.observers.input_schema_audit import (
    run_tomics_haf_input_schema_audit,
)


def _write_inputs_with_treatment_only_dataset3(raw_root: Path) -> None:
    raw_root.mkdir(parents=True, exist_ok=True)
    (raw_root / "2026_2작기_토마토_엽온_과실직경.dat").write_text(
        (
            "timestamp,SolarRad_Avg,LeafTemp1_Avg,LeafTemp2_Avg,Fruit1Diameter_Avg,Fruit2Diameter_Avg\n"
            "2025-09-01 00:00:00,0,20,21,30,31\n"
            "2025-09-01 00:10:00,100,22,23,30.2,31.2\n"
        ),
        encoding="utf-8",
    )
    pd.DataFrame(
        {
            "timestamp": pd.date_range("2025-09-01", periods=2, freq="10min"),
            "loadcell_id": [1, 4],
            "treatment": ["Control", "Drought"],
            "env_inside_radiation_wm2": [0.0, 100.0],
            "env_vpd_kpa": [0.6, 1.1],
            "env_air_temperature_c": [20.0, 24.0],
            "env_co2_ppm": [410.0, 415.0],
            "env_rh_pct": [80.0, 72.0],
            "moisture_percent_mean": [40.0, 35.0],
            "ec_ds_mean": [2.0, 2.2],
            "yield_fresh_g": [5.0, 6.0],
        }
    ).to_parquet(raw_root / "dataset1_loadcell_1_6_daily_ec_moisture_yield_env.parquet", index=False)
    pd.DataFrame(
        {
            "date": pd.to_datetime(["2025-09-01", "2025-09-02"]),
            "loadcell": [4, 5],
            "Treatment": ["Drought", "Drought"],
            "theta": [0.35, 0.36],
            "ec": [2.2, 2.3],
            "tensiometer_hp_mean": [-20.0, -21.0],
        }
    ).to_parquet(raw_root / "dataset2_loadcell_4_5_daily_ec_moisture_tensiometer.parquet", index=False)
    pd.DataFrame(
        {
            "date": pd.to_datetime(["2025-09-01", "2025-09-02"]),
            "sample_id": ["a", "b"],
            "treatment": ["Control", "Drought"],
            "stem_diameter": [9.0, 10.0],
            "flower_height": [18.0, 20.0],
            "flowering_date": pd.to_datetime(["2025-09-10", "2025-09-11"]),
            "cluster": [1, 2],
        }
    ).to_parquet(
        raw_root / "dataset3_individual_stem_diameter_flower_height_flowering_date.parquet",
        index=False,
    )


def test_metadata_contract_records_season_radiation_and_fruit_diameter_rules(tmp_path: Path) -> None:
    raw_root = tmp_path / "raw"
    output_root = tmp_path / "out"
    _write_inputs_with_treatment_only_dataset3(raw_root)

    result = run_tomics_haf_input_schema_audit(
        {"tomics_haf": {"raw_data_root": str(raw_root), "output_root": str(output_root)}},
        repo_root=tmp_path,
    )
    metadata = json.loads(Path(str(result["metadata_json"])).read_text(encoding="utf-8"))

    assert metadata["season_id"] == "2025_2C"
    assert metadata["fixed_clock_daynight_primary"] is False
    assert metadata["clock_06_18_used_only_for_compatibility"] is True
    assert metadata["radiation_thresholds_to_test"] == [0, 1, 5, 10]
    assert metadata["fruit_diameter_rules"]["sensor_level_only"] is True
    assert metadata["fruit_diameter_rules"]["fruit_diameter_treatment_endpoint"] is False
    assert metadata["fruit_diameter_rules"]["fruit_diameter_p_values_allowed"] is False
    assert metadata["fruit_diameter_rules"]["fruit_diameter_allocation_calibration_target"] is False
    assert metadata["Dataset3_mapping_confidence"] == "treatment_level_only"
    assert metadata["VPD_available"] is True
    assert metadata["LAI_available"] is False
    assert metadata["fresh_yield_available"] is True
    assert metadata["dry_yield_available"] is False
    assert metadata["raw_thorp_promoted"] is False
    assert metadata["shipped_TOMICS_incumbent_changed"] is False
