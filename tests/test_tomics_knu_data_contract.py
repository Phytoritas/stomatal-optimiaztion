from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import yaml

from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.data_contract import (
    resolve_knu_data_contract,
    write_data_contract_manifest,
)
from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.datasets.registry import (
    load_dataset_registry,
)
from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.harvest_operator import (
    observed_floor_area_yield,
)
from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.knu_data import load_knu_validation_data


def test_knu_data_contract_resolves_private_root_and_writes_manifest(tmp_path: Path, monkeypatch) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    private_data_root = tmp_path / "private_root" / "data"
    forcing_root = private_data_root / "forcing"
    rootzone_root = private_data_root / "rootzone"
    ec_root = private_data_root / "ec"
    forcing_root.mkdir(parents=True, exist_ok=True)
    rootzone_root.mkdir(parents=True, exist_ok=True)
    ec_root.mkdir(parents=True, exist_ok=True)
    forcing_fixture = repo_root / "tests" / "fixtures" / "knu_sanitized" / "KNU_Tomato_Env_fixture.csv"
    yield_fixture = repo_root / "tests" / "fixtures" / "knu_sanitized" / "tomato_validation_data_yield_fixture.csv"
    (forcing_root / "KNU_Tomato_Env.CSV").write_text(forcing_fixture.read_text(encoding="utf-8"), encoding="utf-8")
    (forcing_root / "tomato_validation_data_yield_260222.csv").write_text(
        yield_fixture.read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    (rootzone_root / "KNU_Tomato_Rootzone.csv").write_text(
        "\n".join(
            [
                "datetime,theta_substrate,slab_weight_kg,sensor_id,zone_id,depth_cm",
                "2025-01-01 00:00:00,0.62,11.4,RZ01,BED01,10",
            ]
        ),
        encoding="utf-8",
    )
    (ec_root / "KNU_Tomato_Rootzone_EC.csv").write_text(
        "\n".join(
            [
                "datetime,rootzone_ec_dS_m,sensor_id,zone_id,depth_cm",
                "2025-01-01 00:00:00,2.8,RZ01,BED01,10",
            ]
        ),
        encoding="utf-8",
    )
    contract_path = tmp_path / "contract.yaml"
    contract_path.write_text(
        yaml.safe_dump(
            {
                "private_data_root_env": "PHYTORITAS_PRIVATE_DATA_ROOT",
                "forcing_relative_path": "data/forcing/KNU_Tomato_Env.CSV",
                "yield_relative_path": "data/forcing/tomato_validation_data_yield_260222.csv",
                "rootzone_relative_path": "data/rootzone/KNU_Tomato_Rootzone.csv",
                "ec_relative_path": "data/ec/KNU_Tomato_Rootzone_EC.csv",
                "reporting_basis": "floor_area_g_m2",
                "plants_per_m2": 1.836091,
                "rootzone_parser_assumptions": {
                    "rootzone_parser": "csv_datetime_first_class",
                    "theta_semantics": "measured_substrate_water_content",
                    "slab_weight_semantics": "measured_substrate_weight",
                    "datetime_policy": "naive_local_greenhouse_timestamps",
                    "missing_policy": "preserve_missing",
                    "long_format": True,
                },
                "ec_parser_assumptions": {
                    "ec_parser": "csv_datetime_first_class",
                    "ec_semantics": "measured_substrate_ec",
                    "datetime_policy": "naive_local_greenhouse_timestamps",
                    "missing_policy": "preserve_missing",
                    "long_format": True,
                },
                "observation": {
                    "date_column": "Date",
                    "measured_cumulative_column": "Measured_Cumulative_Total_Fruit_DW (g/m^2)",
                    "estimated_cumulative_column": "Estimated_Cumulative_Total_Fruit_DW (g/m^2)",
                    "measured_semantics": "cumulative_harvested_fruit_dry_weight_floor_area",
                },
            },
            sort_keys=False,
            allow_unicode=False,
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("PHYTORITAS_PRIVATE_DATA_ROOT", str(tmp_path / "private_root"))
    validation_cfg = {
        "forcing_csv_path": "missing/KNU_Tomato_Env.CSV",
        "yield_xlsx_path": "missing/tomato_validation_data_yield_260222.csv",
        "private_data_contract_path": str(contract_path),
    }
    contract = resolve_knu_data_contract(validation_cfg=validation_cfg, repo_root=repo_root, config_path=contract_path)
    assert contract.forcing_source_kind == "private_root"
    assert contract.yield_source_kind == "private_root"
    assert contract.rootzone_source_kind == "private_root"
    assert contract.ec_source_kind == "private_root"
    assert contract.rootzone_path == rootzone_root / "KNU_Tomato_Rootzone.csv"
    assert contract.ec_path == ec_root / "KNU_Tomato_Rootzone_EC.csv"
    assert contract.date_column == "Date"
    assert contract.measured_cumulative_column == "Measured_Cumulative_Total_Fruit_DW (g/m^2)"
    assert contract.estimated_cumulative_column == "Estimated_Cumulative_Total_Fruit_DW (g/m^2)"
    assert contract.rootzone_parser_assumptions["theta_semantics"] == "measured_substrate_water_content"
    assert contract.ec_parser_assumptions["ec_semantics"] == "measured_substrate_ec"
    data = load_knu_validation_data(forcing_path=contract.forcing_path, yield_path=contract.yield_path)
    manifest_path = write_data_contract_manifest(output_root=tmp_path / "out", contract=contract, data=data)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["reporting_basis"] == "floor_area_g_m2"
    assert manifest["plants_per_m2"] == 1.836091
    assert manifest["observation_columns"]["date"] == "Date"
    assert manifest["parser_assumptions"]["observation_semantics"] == "cumulative_harvested_fruit_dry_weight_floor_area"
    assert manifest["rootzone_source_kind"] == "private_root"
    assert manifest["ec_source_kind"] == "private_root"
    assert manifest["rootzone_source_path"].endswith("KNU_Tomato_Rootzone.csv")
    assert manifest["ec_source_path"].endswith("KNU_Tomato_Rootzone_EC.csv")


def test_load_knu_validation_data_honors_explicit_observation_columns(tmp_path: Path) -> None:
    forcing_path = tmp_path / "forcing.csv"
    forcing_path.write_text(
        "\n".join(
            [
                "datetime,T_air_C,PAR_umol,CO2_ppm,RH_percent,wind_speed_ms",
                "2025-01-01 00:00:00,20,200,400,70,0.5",
                "2025-01-01 01:00:00,20,220,400,69,0.5",
            ]
        ),
        encoding="utf-8",
    )
    yield_path = tmp_path / "yield.csv"
    yield_path.write_text(
        "\n".join(
            [
                "stamp,harvest_obs,harvest_est,notes",
                "2025-01-01,1.0,1.2,a",
                "2025-01-02,2.0,2.2,b",
            ]
        ),
        encoding="utf-8",
    )

    data = load_knu_validation_data(
        forcing_path=forcing_path,
        yield_path=yield_path,
        date_column="stamp",
        measured_column="harvest_obs",
        estimated_column="harvest_est",
    )

    assert data.date_column == "stamp"
    assert data.measured_column == "harvest_obs"
    assert data.estimated_column == "harvest_est"
    assert data.yield_summary["start"].startswith("2025-01-01")
    assert data.yield_summary["end"].startswith("2025-01-02")


def test_observed_floor_area_yield_normalizes_per_plant_input_to_floor_area() -> None:
    yield_df = pd.DataFrame.from_records(
        [
            {"stamp": "2025-01-01", "harvest_obs": 1.0, "harvest_est": 1.5},
            {"stamp": "2025-01-02", "harvest_obs": 2.0, "harvest_est": 2.5},
        ]
    )
    observed = observed_floor_area_yield(
        yield_df=yield_df,
        date_column="stamp",
        measured_column="harvest_obs",
        estimated_column="harvest_est",
        reporting_basis="g_per_plant",
        plants_per_m2=2.0,
    )

    assert observed["measured_cumulative_harvested_fruit_dry_weight_floor_area"].tolist() == [2.0, 4.0]
    assert observed["estimated_cumulative_harvested_fruit_dry_weight_floor_area"].tolist() == [3.0, 5.0]


def test_load_dataset_registry_default_knu_dataset_includes_rootzone_and_ec_management_paths(
    tmp_path: Path,
    monkeypatch,
) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    private_root = tmp_path / "private_root"
    forcing_root = private_root / "data" / "forcing"
    rootzone_root = private_root / "data" / "rootzone"
    ec_root = private_root / "data" / "ec"
    forcing_root.mkdir(parents=True, exist_ok=True)
    rootzone_root.mkdir(parents=True, exist_ok=True)
    ec_root.mkdir(parents=True, exist_ok=True)

    forcing_fixture = repo_root / "tests" / "fixtures" / "knu_sanitized" / "KNU_Tomato_Env_fixture.csv"
    yield_fixture = repo_root / "tests" / "fixtures" / "knu_sanitized" / "tomato_validation_data_yield_fixture.csv"
    (forcing_root / "KNU_Tomato_Env.CSV").write_text(forcing_fixture.read_text(encoding="utf-8"), encoding="utf-8")
    (forcing_root / "tomato_validation_data_yield_260222.csv").write_text(
        yield_fixture.read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    (rootzone_root / "KNU_Tomato_Rootzone.csv").write_text(
        "datetime,theta_substrate,slab_weight_kg,sensor_id,zone_id,depth_cm\n",
        encoding="utf-8",
    )
    (ec_root / "KNU_Tomato_Rootzone_EC.csv").write_text(
        "datetime,rootzone_ec_dS_m,sensor_id,zone_id,depth_cm\n",
        encoding="utf-8",
    )

    contract_path = tmp_path / "contract.yaml"
    contract_path.write_text(
        yaml.safe_dump(
            {
                "private_data_root_env": "PHYTORITAS_PRIVATE_DATA_ROOT",
                "forcing_relative_path": "data/forcing/KNU_Tomato_Env.CSV",
                "yield_relative_path": "data/forcing/tomato_validation_data_yield_260222.csv",
                "rootzone_relative_path": "data/rootzone/KNU_Tomato_Rootzone.csv",
                "ec_relative_path": "data/ec/KNU_Tomato_Rootzone_EC.csv",
                "reporting_basis": "floor_area_g_m2",
                "plants_per_m2": 1.836091,
            },
            sort_keys=False,
            allow_unicode=False,
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("PHYTORITAS_PRIVATE_DATA_ROOT", str(private_root))
    config = {
        "validation": {
            "forcing_csv_path": "missing/KNU_Tomato_Env.CSV",
            "yield_xlsx_path": "missing/tomato_validation_data_yield_260222.csv",
            "private_data_contract_path": str(contract_path),
        }
    }

    dataset = load_dataset_registry(config, repo_root=repo_root, config_path=contract_path).require("knu_actual")

    assert dataset.management.rootzone_path == rootzone_root / "KNU_Tomato_Rootzone.csv"
    assert dataset.management.ec_path == ec_root / "KNU_Tomato_Rootzone_EC.csv"
