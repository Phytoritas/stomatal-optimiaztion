from pathlib import Path

import pandas as pd

from stomatal_optimiaztion.domains.tomato.tomics.observers.legacy_v1_3_bridge import legacy_v1_3_config
from stomatal_optimiaztion.domains.tomato.tomics.observers.yield_bridge import load_legacy_yield_bridge


def test_legacy_5p6_columns_map_to_canonical_dmc_outputs_and_6p5_stays_legacy(tmp_path: Path) -> None:
    archive = tmp_path / "archive"
    source = archive / "outputs/derived/integrated_daily_master_radiation_daynight_fresh_dry.csv"
    source.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(
        {
            "date": ["2025-12-14"],
            "loadcell_id": [4],
            "treatment": ["Drought"],
            "loadcell_daily_yield_g": [1000.0],
            "loadcell_daily_dry_yield_g_est_default_5p6pct": [56.0],
            "loadcell_daily_dry_yield_g_est_6p5pct": [65.0],
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

    bridge, _audit, metadata = load_legacy_yield_bridge(config)

    assert bridge["observed_fruit_FW_g_loadcell"].iloc[0] == 1000.0
    assert bridge["observed_fruit_DW_g_loadcell_dmc_0p056"].iloc[0] == 56.0
    assert bridge["fresh_yield_source"].iloc[0] == str(source)
    assert metadata["canonical_fruit_DMC_fraction"] == 0.056
    assert metadata["DMC_sensitivity_enabled"] is False
    assert "loadcell_daily_dry_yield_g_est_6p5pct" in metadata["legacy_sensitivity_columns_present"]
    assert "dmc_0p065" not in bridge.columns


def test_canonical_dry_column_fills_rows_with_missing_fresh_yield(tmp_path: Path) -> None:
    archive = tmp_path / "archive"
    source = archive / "outputs/derived/integrated_daily_master_radiation_daynight_fresh_dry.csv"
    source.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(
        {
            "date": ["2025-12-14", "2025-12-15"],
            "loadcell_id": [4, 4],
            "treatment": ["Drought", "Drought"],
            "loadcell_daily_yield_g": [1000.0, pd.NA],
            "loadcell_daily_dry_yield_g_est_default_5p6pct": [56.0, 28.0],
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

    bridge, _audit, metadata = load_legacy_yield_bridge(config)

    assert bridge["observed_fruit_FW_g_loadcell"].tolist() == [1000.0, 500.0]
    assert bridge["observed_fruit_DW_g_loadcell_dmc_0p056"].tolist() == [56.0, 28.0]
    assert bridge["dry_yield_source"].tolist() == [
        "fresh_yield_times_canonical_DMC_0p056",
        "legacy_canonical_DMC_0p056_column",
    ]
    assert bridge["fresh_yield_source"].tolist() == [str(source), ""]
    assert metadata["dry_yield_source"] == "fresh_yield_times_canonical_DMC_0p056"
