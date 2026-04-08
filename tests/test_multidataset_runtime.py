from __future__ import annotations

from pathlib import Path

import pandas as pd

from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.datasets.contracts import (
    DatasetBasisContract,
    DatasetManagementMetadata,
    DatasetMetadataContract,
    DatasetObservationContract,
    DatasetSanitizedFixtureContract,
)
from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.datasets.runtime import (
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
    assert bundle.reporting_basis_in == "g_per_plant"
    assert bundle.reporting_basis_canonical == "floor_area_g_m2"
    assert bundle.basis_normalization_resolved is True
    assert bundle.normalization_factor_to_floor_area == 2.0
    assert (bundle.prepared_root / "observation_contract_manifest.json").exists()
