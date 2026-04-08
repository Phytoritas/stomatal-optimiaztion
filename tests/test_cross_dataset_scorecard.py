from __future__ import annotations

import json

import pandas as pd

from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.cross_dataset_scorecard import (
    build_cross_dataset_scorecard,
    build_cross_dataset_scorecard_report,
)
from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.datasets.contracts import (
    DatasetBasisContract,
    DatasetCapability,
    DatasetIngestionStatus,
    DatasetMetadataContract,
    DatasetObservationContract,
    DatasetSanitizedFixtureContract,
)
from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.datasets.registry import (
    DatasetRegistry,
)


def test_cross_dataset_scorecard_aggregates_dataset_rows() -> None:
    dataset_rankings = [
        pd.DataFrame(
            [
                {
                    "dataset_id": "knu_a",
                    "fruit_harvest_family": "dekoning_fds",
                    "leaf_harvest_family": "vegetative_unit_pruning",
                    "fdmc_mode": "dekoning_fds",
                    "mean_score": -10.0,
                    "mean_rmse_cumulative_offset": 5.0,
                    "mean_rmse_daily_increment": 2.0,
                    "max_harvest_mass_balance_error": 0.0,
                    "max_canopy_collapse_days": 3,
                    "mean_native_family_state_fraction": 0.8,
                    "mean_proxy_family_state_fraction": 0.2,
                    "mean_shared_tdvs_proxy_fraction": 0.1,
                    "family_state_mode_distribution": json.dumps({"native_payload": 0.8}),
                    "proxy_mode_used_distribution": json.dumps({"false": 0.8, "true": 0.2}),
                }
            ]
        ),
        pd.DataFrame(
            [
                {
                    "dataset_id": "knu_b",
                    "fruit_harvest_family": "dekoning_fds",
                    "leaf_harvest_family": "vegetative_unit_pruning",
                    "fdmc_mode": "dekoning_fds",
                    "mean_score": -8.0,
                    "mean_rmse_cumulative_offset": 4.0,
                    "mean_rmse_daily_increment": 1.5,
                    "max_harvest_mass_balance_error": 0.0,
                    "max_canopy_collapse_days": 2,
                    "mean_native_family_state_fraction": 0.7,
                    "mean_proxy_family_state_fraction": 0.3,
                    "mean_shared_tdvs_proxy_fraction": 0.2,
                    "family_state_mode_distribution": json.dumps({"native_payload": 0.7}),
                    "proxy_mode_used_distribution": json.dumps({"false": 0.7, "true": 0.3}),
                }
            ]
        ),
    ]
    selected_payloads = [
        {
            "dataset_id": "knu_a",
            "selected_fruit_harvest_family": "dekoning_fds",
            "selected_leaf_harvest_family": "vegetative_unit_pruning",
            "selected_fdmc_mode": "dekoning_fds",
        },
        {
            "dataset_id": "knu_b",
            "selected_fruit_harvest_family": "dekoning_fds",
            "selected_leaf_harvest_family": "vegetative_unit_pruning",
            "selected_fdmc_mode": "dekoning_fds",
        },
    ]
    scorecard = build_cross_dataset_scorecard(dataset_rankings, selected_payloads)
    row = scorecard.iloc[0]
    assert row["dataset_count"] == 2
    assert row["dataset_win_count"] == 2
    assert row["cross_dataset_stability_score"] == 1.0
    assert row["mean_native_family_state_fraction"] == 0.75


def test_cross_dataset_scorecard_report_keeps_registry_breadth_separate_from_denominator() -> None:
    registry = DatasetRegistry(
        datasets=(
            DatasetMetadataContract(
                dataset_id="measured_a",
                dataset_kind="fixture",
                display_name="Measured A",
                dataset_family="public_rda",
                observation_family="yield",
                capability=DatasetCapability.MEASURED_HARVEST,
                ingestion_status=DatasetIngestionStatus.RUNNABLE,
                forcing_path="forcing.csv",
                observed_harvest_path="harvest.csv",
                validation_start="2025-01-01",
                validation_end="2025-01-31",
                basis=DatasetBasisContract(reporting_basis="floor_area_g_m2", plants_per_m2=1.7),
                observation=DatasetObservationContract(date_column="date", measured_cumulative_column="measured"),
                sanitized_fixture=DatasetSanitizedFixtureContract(
                    forcing_fixture_path="forcing.csv",
                    observed_harvest_fixture_path="harvest.csv",
                ),
            ),
            DatasetMetadataContract(
                dataset_id="proxy_b",
                dataset_kind="traitenv_candidate",
                display_name="Proxy B",
                dataset_family="public_bigdata_platform",
                observation_family="yield_environment",
                capability=DatasetCapability.HARVEST_PROXY,
                ingestion_status=DatasetIngestionStatus.DRAFT_NEEDS_RAW_FIXTURE,
                blocker_codes=("missing_raw_fixture",),
            ),
        ),
        default_dataset_ids=("measured_a",),
    )
    dataset_rankings = [
        pd.DataFrame(
            [
                {
                    "dataset_id": "measured_a",
                    "fruit_harvest_family": "dekoning_fds",
                    "leaf_harvest_family": "vegetative_unit_pruning",
                    "fdmc_mode": "dekoning_fds",
                    "mean_score": -8.0,
                    "mean_rmse_cumulative_offset": 4.0,
                    "mean_rmse_daily_increment": 1.5,
                    "max_harvest_mass_balance_error": 0.0,
                    "max_canopy_collapse_days": 2,
                    "mean_native_family_state_fraction": 0.7,
                    "mean_proxy_family_state_fraction": 0.3,
                    "mean_shared_tdvs_proxy_fraction": 0.2,
                    "family_state_mode_distribution": json.dumps({"native_payload": 0.7}),
                    "proxy_mode_used_distribution": json.dumps({"false": 0.7, "true": 0.3}),
                }
            ]
        )
    ]
    selected_payloads = [
        {
            "dataset_id": "measured_a",
            "selected_fruit_harvest_family": "dekoning_fds",
            "selected_leaf_harvest_family": "vegetative_unit_pruning",
            "selected_fdmc_mode": "dekoning_fds",
        }
    ]

    scorecard = build_cross_dataset_scorecard(dataset_rankings, selected_payloads, registry=registry)
    report = build_cross_dataset_scorecard_report(scorecard, registry=registry)

    assert int(scorecard.iloc[0]["runnable_measured_harvest_datasets"]) == 1
    assert int(scorecard.iloc[0]["proxy_datasets"]) == 1
    assert report["dataset_inventory_summary"]["total_registry_datasets"] == 2
    assert report["runnable_measured_dataset_ids"] == ["measured_a"]


def test_cross_dataset_scorecard_report_counts_context_and_blocked_datasets_separately() -> None:
    registry = DatasetRegistry(
        datasets=(
            DatasetMetadataContract(
                dataset_id="measured_a",
                dataset_kind="fixture",
                display_name="Measured A",
                dataset_family="public_rda",
                observation_family="yield",
                capability=DatasetCapability.MEASURED_HARVEST,
                ingestion_status=DatasetIngestionStatus.RUNNABLE,
                forcing_path="forcing.csv",
                observed_harvest_path="harvest.csv",
                validation_start="2025-01-01",
                validation_end="2025-01-31",
                basis=DatasetBasisContract(reporting_basis="floor_area_g_m2", plants_per_m2=1.7),
                observation=DatasetObservationContract(date_column="date", measured_cumulative_column="measured"),
                sanitized_fixture=DatasetSanitizedFixtureContract(
                    forcing_fixture_path="forcing.csv",
                    observed_harvest_fixture_path="harvest.csv",
                ),
            ),
            DatasetMetadataContract(
                dataset_id="measured_basis_blocked",
                dataset_kind="traitenv_candidate",
                display_name="Measured Basis Blocked",
                dataset_family="public_ai_competition",
                observation_family="yield",
                capability=DatasetCapability.MEASURED_HARVEST,
                ingestion_status=DatasetIngestionStatus.DRAFT_NEEDS_BASIS_METADATA,
                forcing_path="forcing.csv",
                observed_harvest_path="harvest.csv",
                validation_start="2025-01-01",
                validation_end="2025-01-31",
                basis=DatasetBasisContract(reporting_basis="unknown", plants_per_m2=None),
                observation=DatasetObservationContract(date_column="date", measured_cumulative_column="measured"),
                sanitized_fixture=DatasetSanitizedFixtureContract(
                    forcing_fixture_path="forcing.csv",
                    observed_harvest_fixture_path="harvest.csv",
                ),
                blocker_codes=("missing_reporting_basis",),
            ),
            DatasetMetadataContract(
                dataset_id="proxy_b",
                dataset_kind="traitenv_candidate",
                display_name="Proxy B",
                dataset_family="public_bigdata_platform",
                observation_family="yield_environment",
                capability=DatasetCapability.HARVEST_PROXY,
                ingestion_status=DatasetIngestionStatus.DRAFT_NEEDS_RAW_FIXTURE,
                blocker_codes=("missing_raw_fixture",),
            ),
            DatasetMetadataContract(
                dataset_id="context_c",
                dataset_kind="traitenv_candidate",
                display_name="Context C",
                dataset_family="school_greenhouse_environment",
                observation_family="environment",
                capability=DatasetCapability.CONTEXT_ONLY,
                ingestion_status=DatasetIngestionStatus.RUNNABLE,
                basis=DatasetBasisContract(reporting_basis="unknown", plants_per_m2=None),
                observation=DatasetObservationContract(),
            ),
        ),
        default_dataset_ids=("measured_a",),
    )
    dataset_rankings = [
        pd.DataFrame(
            [
                {
                    "dataset_id": "measured_a",
                    "fruit_harvest_family": "dekoning_fds",
                    "leaf_harvest_family": "vegetative_unit_pruning",
                    "fdmc_mode": "dekoning_fds",
                    "mean_score": -7.0,
                    "mean_rmse_cumulative_offset": 3.0,
                    "mean_rmse_daily_increment": 1.0,
                    "max_harvest_mass_balance_error": 0.0,
                    "max_canopy_collapse_days": 1,
                    "mean_native_family_state_fraction": 0.9,
                    "mean_proxy_family_state_fraction": 0.1,
                    "mean_shared_tdvs_proxy_fraction": 0.0,
                    "family_state_mode_distribution": json.dumps({"native_payload": 0.9}),
                    "proxy_mode_used_distribution": json.dumps({"false": 0.9, "true": 0.1}),
                }
            ]
        )
    ]
    selected_payloads = [
        {
            "dataset_id": "measured_a",
            "selected_fruit_harvest_family": "dekoning_fds",
            "selected_leaf_harvest_family": "vegetative_unit_pruning",
            "selected_fdmc_mode": "dekoning_fds",
        }
    ]

    scorecard = build_cross_dataset_scorecard(dataset_rankings, selected_payloads, registry=registry)
    report = build_cross_dataset_scorecard_report(scorecard, registry=registry)
    row = scorecard.iloc[0]

    assert int(row["total_registry_datasets"]) == 4
    assert int(row["runnable_measured_harvest_datasets"]) == 1
    assert int(row["proxy_datasets"]) == 1
    assert int(row["context_only_datasets"]) == 1
    assert int(row["blocked_by_missing_raw_fixture"]) == 2
    assert int(row["blocked_by_missing_basis_or_density"]) == 1
    assert report["runnable_measured_dataset_ids"] == ["measured_a"]
    assert report["draft_dataset_ids"] == ["measured_basis_blocked", "proxy_b"]
