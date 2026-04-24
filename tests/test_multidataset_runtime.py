from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.datasets.contracts import (
    DatasetBasisContract,
    DatasetCapability,
    DatasetManagementMetadata,
    DatasetMetadataContract,
    DatasetObservationContract,
    DatasetSanitizedFixtureContract,
)
from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.datasets.runtime import (
    prepare_dataset_runtime_bundle,
    prepare_measured_harvest_bundle,
)


def _write_forcing_fixture(path: Path) -> None:
    pd.DataFrame(
        {
            "datetime": [
                "2025-01-01 00:00:00",
                "2025-01-02 00:00:00",
                "2025-01-03 00:00:00",
            ],
            "T_air_C": [24.0, 24.5, 25.0],
            "PAR_umol": [300.0, 320.0, 340.0],
            "CO2_ppm": [420.0, 425.0, 430.0],
            "RH_percent": [70.0, 72.0, 68.0],
            "wind_speed_ms": [0.4, 0.5, 0.4],
        }
    ).to_csv(path, index=False)


def _write_rootzone_fixture(path: Path) -> None:
    pd.DataFrame(
        {
            "datetime": [
                "2025-01-01 00:00:00",
                "2025-01-02 00:00:00",
                "2025-01-03 00:00:00",
                "2025-01-04 00:00:00",
            ],
            "theta_substrate": [0.63, 0.62, None, 0.61],
            "slab_weight_kg": [11.42, 11.38, 11.36, 11.35],
            "sensor_id": ["RZ01", "RZ01", "RZ01", "RZ01"],
            "zone_id": ["A", "A", "A", "A"],
            "depth_cm": [10, 10, 10, 10],
        }
    ).to_csv(path, index=False)


def _write_rootzone_ec_fixture(path: Path) -> None:
    pd.DataFrame(
        {
            "datetime": [
                "2025-01-01 00:00:00",
                "2025-01-02 00:00:00",
                "2025-01-03 00:00:00",
                "2025-01-04 00:00:00",
            ],
            "rootzone_ec_dS_m": [2.8, 2.9, 3.0, 3.1],
            "sensor_id": ["EC01", "EC01", "EC01", "EC01"],
            "zone_id": ["A", "A", "A", "A"],
            "depth_cm": [10, 10, 10, 10],
        }
    ).to_csv(path, index=False)


def test_prepare_dataset_runtime_bundle_does_not_require_observed_harvest(tmp_path: Path) -> None:
    forcing_path = tmp_path / "forcing.csv"
    _write_forcing_fixture(forcing_path)
    dataset = DatasetMetadataContract(
        dataset_id="context_only",
        dataset_kind="traitenv_bundle",
        display_name="Context-only forcing",
        forcing_path=forcing_path,
        observed_harvest_path=None,
        validation_start="2025-01-01",
        validation_end="2025-01-03",
        cultivar="cv",
        greenhouse="gh",
        season="winter",
        capability=DatasetCapability.CONTEXT_ONLY,
        basis=DatasetBasisContract(reporting_basis="floor_area_g_m2"),
        observation=DatasetObservationContract(),
        management=DatasetManagementMetadata(),
        sanitized_fixture=DatasetSanitizedFixtureContract(forcing_fixture_path=forcing_path),
        notes={"dataset_role_hint": "trait_plus_env_no_harvest"},
    )

    bundle = prepare_dataset_runtime_bundle(
        dataset,
        validation_cfg={
            "resample_rule": "1D",
            "theta_proxy_mode": "bucket_irrigated",
            "theta_proxy_scenarios": ["moderate"],
        },
        prepared_root=tmp_path / "prepared-runtime",
    )

    manifest_path = bundle.prepared_root / "runtime_contract_manifest.json"
    assert bundle.dataset_id == "context_only"
    assert bundle.scenarios["moderate"].forcing_csv_path.exists()
    assert manifest_path.exists()
    assert not (bundle.prepared_root / "observation_contract_manifest.json").exists()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["forcing_path"] == str(forcing_path)
    assert manifest["sanitized_fixture"]["observed_harvest_fixture_path"] is None


def test_prepare_measured_harvest_bundle_honors_contract_columns_and_basis_conversion(tmp_path: Path) -> None:
    forcing_path = tmp_path / "forcing.csv"
    observed_path = tmp_path / "observed.csv"
    _write_forcing_fixture(forcing_path)
    pd.DataFrame(
        {
            "obs_day": ["2025-01-01", "2025-01-02", "2025-01-03"],
            "cum_measured": [1.0, 2.0, 3.0],
            "cum_estimated": [1.1, 2.1, 3.1],
        }
    ).to_csv(observed_path, index=False)
    dataset = DatasetMetadataContract(
        dataset_id="demo_per_plant",
        dataset_kind="measured_harvest",
        display_name="Demo per-plant harvest",
        forcing_path=forcing_path,
        observed_harvest_path=observed_path,
        validation_start="2025-01-02",
        validation_end="2025-01-03",
        cultivar="cv",
        greenhouse="gh",
        season="winter",
        basis=DatasetBasisContract(reporting_basis="g/plant", plants_per_m2=2.0),
        observation=DatasetObservationContract(
            date_column="obs_day",
            measured_cumulative_column="cum_measured",
            estimated_cumulative_column="cum_estimated",
            measured_semantics="cumulative_harvested_fruit_dry_weight_floor_area",
        ),
        management=DatasetManagementMetadata(),
        sanitized_fixture=DatasetSanitizedFixtureContract(
            forcing_fixture_path=forcing_path,
            observed_harvest_fixture_path=observed_path,
        ),
    )
    bundle = prepare_measured_harvest_bundle(
        dataset,
        validation_cfg={
            "resample_rule": "1D",
            "theta_proxy_mode": "bucket_irrigated",
            "theta_proxy_scenarios": ["moderate"],
        },
        prepared_root=tmp_path / "prepared",
    )

    assert list(bundle.observed_df["date"].dt.strftime("%Y-%m-%d")) == ["2025-01-02", "2025-01-03"]
    assert list(bundle.observed_df["measured_cumulative_total_fruit_dry_weight_floor_area"]) == [4.0, 6.0]
    assert list(bundle.observed_df["estimated_cumulative_total_fruit_dry_weight_floor_area"]) == [4.2, 6.2]
    forcing_df = pd.read_csv(bundle.scenarios["moderate"].forcing_csv_path)
    assert list(pd.to_datetime(forcing_df["datetime"]).dt.strftime("%Y-%m-%d")) == ["2025-01-02", "2025-01-03"]
    assert bundle.reporting_basis_in == "g_per_plant"
    assert bundle.reporting_basis_canonical == "floor_area_g_m2"
    assert bundle.basis_normalization_resolved is True
    assert bundle.normalization_factor_to_floor_area == 2.0
    assert (bundle.prepared_root / "observation_contract_manifest.json").exists()


def test_prepare_measured_harvest_bundle_loads_optional_rootzone_measurements(tmp_path: Path) -> None:
    forcing_path = tmp_path / "forcing.csv"
    observed_path = tmp_path / "observed.csv"
    rootzone_path = tmp_path / "rootzone.csv"
    rootzone_ec_path = tmp_path / "rootzone_ec.csv"
    _write_forcing_fixture(forcing_path)
    _write_rootzone_fixture(rootzone_path)
    _write_rootzone_ec_fixture(rootzone_ec_path)
    pd.DataFrame(
        {
            "Date": ["2025-01-02", "2025-01-03"],
            "Measured_Cumulative_Total_Fruit_DW (g/m^2)": [2.0, 3.0],
        }
    ).to_csv(observed_path, index=False)
    dataset = DatasetMetadataContract(
        dataset_id="demo_rootzone",
        dataset_kind="measured_harvest",
        display_name="Demo rootzone harvest",
        forcing_path=forcing_path,
        observed_harvest_path=observed_path,
        validation_start="2025-01-02",
        validation_end="2025-01-03",
        cultivar="cv",
        greenhouse="gh",
        season="winter",
        basis=DatasetBasisContract(reporting_basis="floor_area_g_m2"),
        observation=DatasetObservationContract(
            date_column="Date",
            measured_cumulative_column="Measured_Cumulative_Total_Fruit_DW (g/m^2)",
            measured_semantics="cumulative_harvested_fruit_dry_weight_floor_area",
        ),
        management=DatasetManagementMetadata(
            rootzone_path=rootzone_path,
            ec_path=rootzone_ec_path,
        ),
        sanitized_fixture=DatasetSanitizedFixtureContract(
            forcing_fixture_path=forcing_path,
            observed_harvest_fixture_path=observed_path,
        ),
    )

    bundle = prepare_measured_harvest_bundle(
        dataset,
        validation_cfg={
            "resample_rule": "1D",
            "theta_proxy_mode": "bucket_irrigated",
            "theta_proxy_scenarios": ["moderate"],
        },
        prepared_root=tmp_path / "prepared",
    )

    assert bundle.rootzone_df is not None
    assert bundle.rootzone_ec_df is not None
    assert list(bundle.rootzone_df["datetime"].dt.strftime("%Y-%m-%d")) == ["2025-01-02", "2025-01-03"]
    assert list(bundle.rootzone_ec_df["datetime"].dt.strftime("%Y-%m-%d")) == ["2025-01-02", "2025-01-03"]
    assert bundle.rootzone_df["theta_substrate"].isna().sum() == 1
    assert bundle.rootzone_summary["rootzone"]["rows"] == 2
    assert bundle.rootzone_summary["rootzone"]["non_null_counts"]["theta_substrate"] == 1
    manifest = json.loads((bundle.prepared_root / "observation_contract_manifest.json").read_text(encoding="utf-8"))
    assert manifest["management"]["rootzone_path"] == str(rootzone_path)
    assert manifest["management"]["ec_path"] == str(rootzone_ec_path)
    assert manifest["rootzone_measurements"]["derived_rootzone_stress_metrics_included"] is False
