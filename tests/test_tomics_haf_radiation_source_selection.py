from __future__ import annotations

import pandas as pd

from stomatal_optimiaztion.domains.tomato.tomics.observers.radiation_source import (
    build_radiation_source_verification,
)


def _audit_row(*, filename: str, resolution: float) -> dict[str, object]:
    return {
        "expected_filename": filename,
        "date_min": "2025-09-01T00:00:00",
        "date_max": "2025-09-01T00:20:00",
        "inferred_time_resolution_seconds": resolution,
    }


def test_dataset1_inside_radiation_is_selected_over_lower_ranked_fallbacks() -> None:
    dataset1 = pd.DataFrame(
        {
            "timestamp": pd.date_range("2025-09-01", periods=3, freq="10min"),
            "env_inside_radiation_wm2": [0.0, 50.0, 0.0],
            "env_radiation_wm2": [0.0, 80.0, 0.0],
            "env_outside_radiation_wm2": [0.0, 120.0, 0.0],
        }
    )
    raw_dat = pd.DataFrame(
        {
            "timestamp": pd.date_range("2025-09-01", periods=3, freq="10min"),
            "SolarRad_Avg": [0.0, 200.0, 0.0],
        }
    )

    rows, metadata = build_radiation_source_verification(
        {"dataset1": dataset1, "fruit_leaf_temperature_solar_raw_dat": raw_dat},
        {
            "dataset1": _audit_row(filename="dataset1.parquet", resolution=600),
            "fruit_leaf_temperature_solar_raw_dat": _audit_row(filename="raw.dat", resolution=600),
        },
    )

    chosen = [row for row in rows if row["chosen_primary"]]
    assert len(chosen) == 1
    assert chosen[0]["source_file_role"] == "dataset1"
    assert chosen[0]["candidate_column"] == "env_inside_radiation_wm2"
    assert metadata["dataset1_radiation_directly_usable"] is True
    assert metadata["fallback_required"] is False
    assert metadata["fixed_clock_daynight_primary"] is False


def test_dataset1_daily_only_radiation_is_not_usable_for_10min_and_raw_dat_is_fallback() -> None:
    dataset1 = pd.DataFrame(
        {
            "date": pd.to_datetime(["2025-09-01", "2025-09-02"]),
            "env_inside_radiation_wm2": [120.0, 80.0],
            "env_radiation_wm2_mean": [118.0, 79.0],
        }
    )
    raw_dat = pd.DataFrame(
        {
            "timestamp": pd.date_range("2025-09-01", periods=3, freq="10min"),
            "SolarRad_Avg": [0.0, 250.0, 0.0],
        }
    )

    rows, metadata = build_radiation_source_verification(
        {"dataset1": dataset1, "fruit_leaf_temperature_solar_raw_dat": raw_dat},
        {
            "dataset1": _audit_row(filename="dataset1.parquet", resolution=86_400),
            "fruit_leaf_temperature_solar_raw_dat": _audit_row(filename="raw.dat", resolution=600),
        },
    )

    chosen = [row for row in rows if row["chosen_primary"]][0]
    raw_candidate = [
        row
        for row in rows
        if row["source_file_role"] == "fruit_leaf_temperature_solar_raw_dat"
        and row["candidate_column"] == "SolarRad_Avg"
    ][0]
    assert chosen["candidate_column"] == "env_inside_radiation_wm2"
    assert chosen["usable_for_10min_daynight"] is False
    assert chosen["usable_for_daily_summary_only"] is True
    assert metadata["dataset1_radiation_directly_usable"] is False
    assert metadata["dataset1_radiation_grain"] == "daily_only"
    assert metadata["radiation_daynight_primary_source"] == ""
    assert metadata["radiation_column_used"] == ""
    assert metadata["fallback_required"] is True
    assert metadata["fallback_source_if_required"] == "fruit_leaf_temperature_solar_raw_dat:SolarRad_Avg"
    assert raw_candidate["fallback_reason"] == "10min_daynight_candidate_if_primary_is_daily_or_unusable"


def test_raw_dat_remains_fallback_only_when_dataset1_radiation_is_missing() -> None:
    dataset1 = pd.DataFrame(
        {
            "timestamp": pd.date_range("2025-09-01", periods=3, freq="10min"),
            "env_vpd_kpa": [0.5, 0.8, 0.6],
        }
    )
    raw_dat = pd.DataFrame(
        {
            "timestamp": pd.date_range("2025-09-01", periods=3, freq="10min"),
            "SolarRad_Avg": [0.0, 250.0, 0.0],
        }
    )

    rows, metadata = build_radiation_source_verification(
        {"dataset1": dataset1, "fruit_leaf_temperature_solar_raw_dat": raw_dat},
        {
            "dataset1": _audit_row(filename="dataset1.parquet", resolution=600),
            "fruit_leaf_temperature_solar_raw_dat": _audit_row(filename="raw.dat", resolution=600),
        },
    )

    raw_candidate = [
        row
        for row in rows
        if row["source_file_role"] == "fruit_leaf_temperature_solar_raw_dat"
        and row["candidate_column"] == "SolarRad_Avg"
    ][0]
    assert [row for row in rows if row["chosen_primary"]] == []
    assert raw_candidate["chosen_primary"] is False
    assert metadata["radiation_daynight_primary_source"] == ""
    assert metadata["radiation_column_used"] == ""
    assert metadata["dataset1_radiation_directly_usable"] is False
    assert metadata["fallback_required"] is True
    assert metadata["fallback_source_if_required"] == "fruit_leaf_temperature_solar_raw_dat:SolarRad_Avg"


def test_raw_dat_is_not_primary_when_dataset1_inside_radiation_is_usable() -> None:
    dataset1 = pd.DataFrame({"env_inside_radiation_wm2": [0.0, 1.0]})
    raw_dat = pd.DataFrame({"SolarRad_Avg": [0.0, 1000.0]})

    rows, metadata = build_radiation_source_verification(
        {"dataset1": dataset1, "fruit_leaf_temperature_solar_raw_dat": raw_dat},
        {
            "dataset1": _audit_row(filename="dataset1.parquet", resolution=600),
            "fruit_leaf_temperature_solar_raw_dat": _audit_row(filename="raw.dat", resolution=600),
        },
    )

    raw_candidate = [
        row
        for row in rows
        if row["source_file_role"] == "fruit_leaf_temperature_solar_raw_dat"
        and row["candidate_column"] == "SolarRad_Avg"
    ][0]
    assert metadata["radiation_column_used"] == "env_inside_radiation_wm2"
    assert raw_candidate["chosen_primary"] is False
