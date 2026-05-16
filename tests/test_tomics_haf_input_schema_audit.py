from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from stomatal_optimiaztion.domains.tomato.tomics.observers.input_schema_audit import (
    DEFAULT_INPUT_FILE_SPECS,
    audit_input_file,
    match_semantic_roles,
    run_tomics_haf_input_schema_audit,
)


def _write_default_synthetic_inputs(raw_root: Path, *, include_dataset3: bool = True) -> None:
    raw_root.mkdir(parents=True, exist_ok=True)
    (raw_root / "2026_2작기_토마토_엽온_과실직경.dat").write_text(
        (
            '"TOA5","CR1000XSeries","CR1000X","30553","CR1000X.Std.08.01","CPU","2368","min10"\n'
            '"TIMESTAMP","RECORD","LeafTemp1_Avg","LeafTemp2_Avg","Fruit1Diameter_Avg",'
            '"Fruit2Diameter_Avg","SolarRad_Avg"\n'
            '"TS","RN","Deg C","Deg C","mm","mm","W/m2"\n'
            '"","","Avg","Avg","Avg","Avg","Avg"\n'
            '"2025-09-01 00:00:00",0,20.1,20.2,31.0,30.5,0\n'
            '"2025-09-01 00:10:00",1,21.1,21.2,31.1,30.6,150\n'
        ),
        encoding="utf-8",
    )
    pd.DataFrame(
        {
            "timestamp": pd.date_range("2025-09-01", periods=2, freq="10min"),
            "loadcell_id": [1, 4],
            "treatment": ["Control", "Drought"],
            "env_inside_radiation_wm2": [0.0, 120.0],
            "env_radiation_wm2": [0.0, 100.0],
            "env_vpd_kpa": [0.5, 1.2],
            "env_air_temperature_c": [22.0, 24.0],
            "env_co2_ppm": [420.0, 430.0],
            "env_rh_pct": [75.0, 70.0],
            "moisture_percent_mean": [43.0, 38.0],
            "ec_ds_mean": [2.1, 2.3],
            "yield_fresh_g": [10.0, 12.0],
            "yield_dry_g": [0.65, 0.78],
            "LAI": [2.1, 2.2],
        }
    ).to_parquet(raw_root / "dataset1_loadcell_1_6_daily_ec_moisture_yield_env.parquet", index=False)
    pd.DataFrame(
        {
            "date": pd.to_datetime(["2025-09-01", "2025-09-02"]),
            "loadcell": [4, 5],
            "Treatment": ["Drought", "Drought"],
            "substrate_moisture": [35.0, 36.0],
            "EC": [2.4, 2.5],
            "tensiometer": [-20.0, -22.0],
        }
    ).to_parquet(raw_root / "dataset2_loadcell_4_5_daily_ec_moisture_tensiometer.parquet", index=False)
    if include_dataset3:
        pd.DataFrame(
            {
                "date": pd.to_datetime(["2025-09-01", "2025-09-02"]),
                "sample_id": ["p1", "p2"],
                "loadcell_id": [1, 4],
                "treatment": ["Control", "Drought"],
                "stem_diameter_mm": [9.5, 10.1],
                "flower_cluster_height": [20.0, 22.0],
                "flowering_date": pd.to_datetime(["2025-09-10", "2025-09-11"]),
                "truss": [1, 1],
            }
        ).to_parquet(
            raw_root / "dataset3_individual_stem_diameter_flower_height_flowering_date.parquet",
            index=False,
        )


def _config(raw_root: Path, output_root: Path) -> dict[str, object]:
    return {
        "tomics_haf": {
            "raw_data_root": str(raw_root),
            "output_root": str(output_root),
        }
    }


def test_alias_matching_for_requested_roles() -> None:
    roles = match_semantic_roles(
        [
            "TIMESTAMP",
            "Loadcell",
            "Treatment",
            "env_inside_radiation_wm2",
            "VPD_kPa",
            "substrate_moisture",
            "EC",
            "harvest_fresh_weight_g",
            "fruit_dry_weight_g",
        ]
    )

    assert roles["datetime"] == ["TIMESTAMP"]
    assert roles["loadcell"] == ["Loadcell"]
    assert roles["treatment"] == ["Treatment"]
    assert roles["radiation"] == ["env_inside_radiation_wm2"]
    assert roles["vpd"] == ["VPD_kPa"]
    assert roles["moisture"] == ["substrate_moisture"]
    assert roles["ec"] == ["EC"]
    assert roles["yield_fresh"] == ["harvest_fresh_weight_g"]
    assert roles["yield_dry"] == ["fruit_dry_weight_g"]


def test_input_schema_audit_writes_expected_outputs_with_synthetic_parquet_and_dat(tmp_path: Path) -> None:
    raw_root = tmp_path / "raw"
    output_root = tmp_path / "out"
    _write_default_synthetic_inputs(raw_root)

    result = run_tomics_haf_input_schema_audit(
        _config(raw_root, output_root),
        repo_root=tmp_path,
    )

    input_csv = Path(str(result["input_schema_audit_csv"]))
    input_json = Path(str(result["input_schema_audit_json"]))
    assert input_csv.exists()
    assert input_json.exists()
    rows = pd.read_csv(input_csv)
    assert rows.shape[0] == len(DEFAULT_INPUT_FILE_SPECS)
    assert set(rows["status"]).issubset({"ok", "ok_with_warnings"})
    dataset1 = rows.loc[rows["file_role"].eq("dataset1")].iloc[0]
    assert dataset1["parser_used"] == "pandas.read_parquet"
    assert dataset1["loadcell_column"] == "loadcell_id"
    assert json.loads(dataset1["loadcell_ids_json"]) == [1, 4]
    assert "radiation" in json.loads(dataset1["matched_semantic_roles_json"])


def test_missing_required_file_returns_missing_file_without_crashing(tmp_path: Path) -> None:
    missing_path = tmp_path / "missing.parquet"

    row, frame = audit_input_file(
        file_role="dataset1",
        expected_filename="missing.parquet",
        resolved_path=missing_path,
    )

    assert frame is None
    assert row["exists"] is False
    assert row["status"] == "missing_file"
    assert row["row_count"] is None


def test_dataset1_missing_datetime_or_date_returns_missing_required_column(tmp_path: Path) -> None:
    path = tmp_path / "dataset1.csv"
    path.write_text(
        (
            "loadcell_id,treatment,env_inside_radiation_wm2,env_vpd_kpa,env_air_temperature_c,"
            "env_co2_ppm,env_rh_pct,moisture_percent_mean,ec_ds_mean,yield_fresh_g,yield_dry_g,LAI\n"
            "1,Control,0,0.5,22,420,75,43,2.1,10,0.6,2.1\n"
        ),
        encoding="utf-8",
    )

    row, frame = audit_input_file(
        file_role="dataset1",
        expected_filename="dataset1.csv",
        resolved_path=path,
    )

    assert frame is not None
    assert row["status"] == "missing_required_column"
    assert "datetime_or_date" in json.loads(str(row["missing_important_roles_json"]))


def test_dataset1_missing_radiation_is_unsafe_for_primary_use(tmp_path: Path) -> None:
    path = tmp_path / "dataset1.csv"
    path.write_text(
        (
            "timestamp,loadcell_id,treatment,env_vpd_kpa,env_air_temperature_c,"
            "env_co2_ppm,env_rh_pct,moisture_percent_mean,ec_ds_mean,yield_fresh_g,yield_dry_g,LAI\n"
            "2025-09-01 00:00:00,1,Control,0.5,22,420,75,43,2.1,10,0.6,2.1\n"
        ),
        encoding="utf-8",
    )

    row, frame = audit_input_file(
        file_role="dataset1",
        expected_filename="dataset1.csv",
        resolved_path=path,
    )

    assert frame is not None
    assert row["status"] == "unsafe_for_primary_use"
    assert "radiation" in json.loads(str(row["missing_important_roles_json"]))


def test_parse_failed_status_is_reported_without_crashing(tmp_path: Path) -> None:
    path = tmp_path / "dataset1.bin"
    path.write_bytes(b"not a supported tabular file")

    row, frame = audit_input_file(
        file_role="dataset1",
        expected_filename="dataset1.bin",
        resolved_path=path,
    )

    assert frame is None
    assert row["status"] == "parse_failed"
    assert row["parser_used"] == "unsupported"
