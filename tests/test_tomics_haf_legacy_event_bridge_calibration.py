from pathlib import Path

import pandas as pd
import pytest

from stomatal_optimiaztion.domains.tomato.tomics.observers.event_bridge_calibration import (
    CALIBRATION_TOTAL_COL,
    calibration_match_metadata,
    load_legacy_event_bridge_daily_totals,
)
from stomatal_optimiaztion.domains.tomato.tomics.observers.legacy_v1_3_bridge import legacy_v1_3_config
from stomatal_optimiaztion.domains.tomato.tomics.observers.water_flux_event_bridge import (
    calibrate_to_daily_event_bridged_total,
)


def _write_legacy_event_bridge(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(
        {
            "date": ["2025-12-14"],
            "loadcell_id": [4],
            "treatment": ["Drought"],
            "event_bridged_loss_g_per_day": [100.0],
            "primary_event_bridge_qc": [True],
            "valid_coverage_fraction": [1.0],
            "event_bridge_rate_source": ["legacy"],
            "bridge_to_quiet_scaled_ratio": [1.2],
        }
    ).to_csv(path, index=False)


def test_legacy_event_bridge_daily_totals_calibrate_matching_intervals(tmp_path: Path) -> None:
    archive = tmp_path / "archive"
    candidate = archive / "previous_outputs/event_bridge_outputs/daily_event_bridged_transpiration.csv"
    _write_legacy_event_bridge(candidate)
    config = legacy_v1_3_config(
        {
            "legacy_v1_3": {
                "enabled": True,
                "archive_root": str(archive),
                "allow_legacy_event_bridge_calibration": True,
            }
        },
        repo_root=tmp_path,
    )

    daily_totals, audit, metadata = load_legacy_event_bridge_daily_totals(config)
    intervals = pd.DataFrame(
        {
            "date": ["2025-12-14", "2025-12-14"],
            "loadcell_id": [4, 4],
            "treatment": ["Drought", "Drought"],
            "loss_g_10min_unscaled": [20.0, 30.0],
        }
    )
    calibrated = calibrate_to_daily_event_bridged_total(
        intervals,
        daily_totals,
        total_col=CALIBRATION_TOTAL_COL,
    )
    matched_metadata = calibration_match_metadata(calibrated, daily_totals, metadata)

    assert audit["status"].iloc[0] == "ok"
    assert metadata["existing_daily_event_bridged_total_available"] is True
    assert calibrated["daily_bridge_scale_factor"].iloc[0] == pytest.approx(2.0)
    assert calibrated["loss_g_10min_event_bridged_calibrated"].sum() == pytest.approx(100.0)
    assert matched_metadata["event_bridged_ET_calibration_status"] == "calibrated_to_legacy_daily_event_total"
    assert matched_metadata["event_bridged_ET_calibration_provenance"] == "legacy_v1_3_derived_output"
    assert matched_metadata["event_bridged_ET_calibration_direct_raw_recomputed"] is False


def test_legacy_event_bridge_rejects_non_finite_daily_totals(tmp_path: Path) -> None:
    archive = tmp_path / "archive"
    candidate = archive / "previous_outputs/event_bridge_outputs/daily_event_bridged_transpiration.csv"
    candidate.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(
        {
            "date": ["2025-12-14"],
            "loadcell_id": [4],
            "treatment": ["Drought"],
            "event_bridged_loss_g_per_day": [float("inf")],
            "valid_coverage_fraction": [1.0],
        }
    ).to_csv(candidate, index=False)
    config = legacy_v1_3_config(
        {
            "legacy_v1_3": {
                "enabled": True,
                "archive_root": str(archive),
                "allow_legacy_event_bridge_calibration": True,
            }
        },
        repo_root=tmp_path,
    )

    daily_totals, audit, metadata = load_legacy_event_bridge_daily_totals(config)

    assert daily_totals.empty
    assert audit["status"].iloc[0] == "no_usable_rows"
    assert metadata["existing_daily_event_bridged_total_available"] is False
