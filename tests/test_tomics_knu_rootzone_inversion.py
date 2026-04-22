from __future__ import annotations

from pathlib import Path

import pandas as pd

from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.knu_data import read_knu_forcing_csv
from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.rootzone_inversion import (
    _recharge_event_count,
    reconstruct_rootzone,
)


def test_rootzone_inversion_writes_uncertainty_band_from_fixture() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    forcing = read_knu_forcing_csv(repo_root / "tests" / "fixtures" / "knu_sanitized" / "KNU_Tomato_Env_fixture.csv")
    result = reconstruct_rootzone(forcing, theta_proxy_mode="bucket_irrigated")
    assert {"dry", "moderate", "wet"} == set(result.scenario_frames)
    assert not result.summary_df.empty
    assert "proxy_uncertainty_width" in result.band_df.columns
    assert float(result.band_df["proxy_uncertainty_width"].max()) >= 0.0
    assert result.manifest["measured_rootzone"]["used"] is False


def test_rootzone_inversion_adds_measured_theta_scenario_with_labeled_mean_fill() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    forcing = read_knu_forcing_csv(repo_root / "tests" / "fixtures" / "knu_sanitized" / "KNU_Tomato_Env_fixture.csv")
    measured = forcing[["datetime"]].copy()
    measured["theta_substrate"] = [0.60, None, 0.62, 0.63, *([0.61] * (len(measured) - 4))]
    measured["sensor_id"] = "RZ01"
    measured["zone_id"] = "A"
    measured["depth_cm"] = 10

    result = reconstruct_rootzone(
        forcing,
        theta_proxy_mode="bucket_irrigated",
        scenario_ids=("moderate",),
        measured_rootzone_df=measured,
        measured_theta_coverage_min=0.50,
    )

    assert {"moderate", "measured"} == set(result.scenario_frames)
    measured_frame = result.scenario_frames["measured"]
    assert "filled_with_period_mean" in set(measured_frame["theta_measurement_source"])
    assert measured_frame["theta_substrate"].between(0.40, 0.85).all()
    assert result.manifest["measured_rootzone"]["used"] is True
    assert result.manifest["measured_rootzone"]["filled_row_count"] == 1
    summary = result.summary_df.set_index("theta_proxy_scenario")
    assert summary.loc["measured", "theta_source"] == "measured_rootzone"


def test_rootzone_inversion_skips_measured_theta_when_alignment_has_no_coverage() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    forcing = read_knu_forcing_csv(repo_root / "tests" / "fixtures" / "knu_sanitized" / "KNU_Tomato_Env_fixture.csv")
    measured = forcing[["datetime"]].copy()
    measured["datetime"] = measured["datetime"] + pd.Timedelta(days=365)
    measured["theta_substrate"] = 0.62

    result = reconstruct_rootzone(
        forcing,
        theta_proxy_mode="bucket_irrigated",
        scenario_ids=("moderate",),
        measured_rootzone_df=measured,
        measured_theta_coverage_min=0.50,
    )

    assert {"moderate"} == set(result.scenario_frames)
    assert result.manifest["measured_rootzone"]["used"] is False
    assert result.manifest["measured_rootzone"]["skip_reason"] == "coverage_below_minimum"


def test_rootzone_inversion_uses_sparse_measured_theta_when_threshold_allows() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    forcing = read_knu_forcing_csv(repo_root / "tests" / "fixtures" / "knu_sanitized" / "KNU_Tomato_Env_fixture.csv")
    measured = forcing[["datetime"]].iloc[[0]].copy()
    measured["theta_substrate"] = 0.62

    result = reconstruct_rootzone(
        forcing,
        theta_proxy_mode="bucket_irrigated",
        scenario_ids=("moderate",),
        measured_rootzone_df=measured,
        measured_theta_coverage_min=0.05,
    )

    assert {"moderate", "measured"} == set(result.scenario_frames)
    assert result.manifest["measured_rootzone"]["used"] is True
    assert result.manifest["measured_rootzone"]["coverage_fraction"] >= 0.05


def test_recharge_event_count_counts_rising_edges_not_flagged_timesteps() -> None:
    frame = read_knu_forcing_csv(
        Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "knu_sanitized" / "KNU_Tomato_Env_fixture.csv"
    )
    frame["irrigation_proxy_flag"] = [0, 1, 1, 0, 1, 1, 1, 0, 0, 1, 0, 0, 1, 1, 0, 0]
    assert _recharge_event_count(frame) == 4
