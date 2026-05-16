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
    assert metadata["canonical_fruit_DMC_fraction"] == 0.056
    assert metadata["fruit_DMC_fraction"] == 0.056
    assert metadata["default_fruit_dry_matter_content"] == 0.056
    assert metadata["DMC_fixed_for_2025_2C"] is True
    assert metadata["DMC_sensitivity_enabled"] is False
    assert metadata["DMC_sensitivity_values"] == []
    assert metadata["deprecated_previous_default_fruit_DMC_fraction"] == 0.065
    assert metadata["default_fruit_dry_matter_content_from_legacy"] == 0.056
    assert bridge["observed_fruit_FW_g_loadcell"].iloc[0] == 120.0
    assert bridge["observed_fruit_DW_g_loadcell_dmc_0p056"].iloc[0] == 6.72
    assert bridge["dry_yield_source"].iloc[0] == "fresh_yield_times_canonical_DMC_0p056"
    assert "loadcell_daily_dry_yield_g_est_lower_5p2pct" in metadata["legacy_sensitivity_columns_present"]


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
    assert bridge["observed_fruit_DW_g_loadcell_dmc_0p056"].iloc[0] == 16.8
    assert metadata["fresh_yield_available"] is True
    assert metadata["dry_yield_available"] is True
    assert metadata["legacy_yield_bridge_used"] is True
