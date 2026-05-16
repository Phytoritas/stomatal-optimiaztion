from pathlib import Path

import pandas as pd

from stomatal_optimiaztion.domains.tomato.tomics.observers.legacy_v1_3_bridge import legacy_v1_3_config
from stomatal_optimiaztion.domains.tomato.tomics.observers.yield_bridge import load_legacy_yield_bridge


def test_legacy_yield_bridge_distinguishes_fresh_from_dmc_estimated_dry_yield(tmp_path: Path) -> None:
    archive = tmp_path / "archive"
    source = archive / "outputs/derived/integrated_daily_master_radiation_daynight_fresh_dry.csv"
    source.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(
        {
            "date": ["2025-12-14"],
            "loadcell_id": [4],
            "treatment": ["Drought"],
            "loadcell_daily_yield_g": [120.0],
            "loadcell_cumulative_yield_g": [300.0],
            "loadcell_daily_dry_yield_g_est_default_5p6pct": [6.72],
            "loadcell_daily_dry_yield_g_est_lower_5p2pct": [6.24],
            "loadcell_daily_dry_yield_g_est_upper_6p0pct": [7.2],
            "loadcell_daily_dry_yield_g_est_broad_low_4pct": [4.8],
            "loadcell_daily_dry_yield_g_est_broad_high_8pct": [9.6],
        }
    ).to_csv(source, index=False)
    config = legacy_v1_3_config(
        {
            "legacy_v1_3": {
                "enabled": True,
                "archive_root": str(archive),
                "allow_legacy_yield_bridge": True,
                "direct_dry_yield_measured": False,
            }
        },
        repo_root=tmp_path,
    )

    bridge, audit, metadata = load_legacy_yield_bridge(config)

    assert audit["status"].iloc[0] == "ok"
    assert bridge["measured_or_legacy_fresh_yield_g"].iloc[0] == 120.0
    assert bool(bridge["dry_yield_is_dmc_estimated"].iloc[0]) is True
    assert bool(bridge["direct_dry_yield_measured"].iloc[0]) is False
    assert metadata["fresh_yield_available"] is True
    assert metadata["dry_yield_available"] is True
    assert metadata["dry_yield_is_dmc_estimated"] is True
    assert metadata["direct_dry_yield_measured"] is False
    assert metadata["default_fruit_dry_matter_content_from_legacy"] == 0.056
    assert metadata["configured_default_fruit_dry_matter_content"] == 0.065
    assert 0.04 in metadata["dmc_sensitivity"]


def test_legacy_yield_bridge_accepts_cumulative_fresh_yield_without_daily_yield(tmp_path: Path) -> None:
    archive = tmp_path / "archive"
    source = archive / "outputs/derived/integrated_daily_master_radiation_daynight_fresh_dry.csv"
    source.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(
        {
            "date": ["2025-12-14"],
            "loadcell_id": [4],
            "treatment": ["Drought"],
            "loadcell_cumulative_yield_g": [300.0],
        }
    ).to_csv(source, index=False)
    config = legacy_v1_3_config(
        {
            "legacy_v1_3": {
                "enabled": True,
                "archive_root": str(archive),
                "allow_legacy_yield_bridge": True,
                "direct_dry_yield_measured": False,
            }
        },
        repo_root=tmp_path,
    )

    bridge, audit, metadata = load_legacy_yield_bridge(config)

    assert audit["status"].iloc[0] == "ok"
    assert bridge["measured_or_legacy_fresh_yield_g"].iloc[0] == 300.0
    assert metadata["fresh_yield_available"] is True
    assert metadata["dry_yield_available"] is False
    assert metadata["legacy_yield_bridge_used"] is True
