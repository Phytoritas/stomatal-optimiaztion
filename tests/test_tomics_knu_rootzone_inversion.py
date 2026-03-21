from __future__ import annotations

from pathlib import Path

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
    assert "Measured root-zone variables may override the proxy in future runs if supplied." in result.manifest["assumptions"]


def test_recharge_event_count_counts_rising_edges_not_flagged_timesteps() -> None:
    frame = read_knu_forcing_csv(
        Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "knu_sanitized" / "KNU_Tomato_Env_fixture.csv"
    )
    frame["irrigation_proxy_flag"] = [0, 1, 1, 0, 1, 1, 1, 0, 0, 1, 0, 0, 1, 1, 0, 0]
    assert _recharge_event_count(frame) == 4
