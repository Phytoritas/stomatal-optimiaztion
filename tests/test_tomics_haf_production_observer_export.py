from pathlib import Path

import pandas as pd

from stomatal_optimiaztion.domains.tomato.tomics.observers.contracts import DATASET1_COLUMN_CANDIDATES
from stomatal_optimiaztion.domains.tomato.tomics.observers.production_export import (
    aggregate_dataset1_streaming,
)
from stomatal_optimiaztion.domains.tomato.tomics.observers.pipeline import _dataset3_size_guard
from stomatal_optimiaztion.domains.tomato.tomics.observers.pipeline import _assert_dataset3_size_guard_before_read
from stomatal_optimiaztion.domains.tomato.tomics.observers.radiation_windows import build_radiation_intervals


def test_chunked_dataset1_interval_aggregation_matches_non_chunked(tmp_path: Path) -> None:
    frame = pd.DataFrame(
        {
            "timestamp": pd.to_datetime(
                [
                    "2025-12-14 06:00:00",
                    "2025-12-14 06:03:00",
                    "2025-12-14 06:10:00",
                    "2025-12-14 06:11:00",
                ]
            ),
            "date": ["2025-12-14"] * 4,
            "loadcell_id": [1, 1, 1, 1],
            "sample_id": [1, 1, 1, 1],
            "treatment": ["Control"] * 4,
            "loadcell_weight_kg": [10.0, 9.99, 9.98, 9.97],
            "env_inside_radiation_wm2": [0.0, 0.5, 0.0, 5.0],
            "env_vpd_kpa": [2.0, 2.0, 3.0, 3.0],
            "env_air_temperature_c": [25.0] * 4,
            "env_co2_ppm": [400.0] * 4,
        }
    )
    path = tmp_path / "dataset1.parquet"
    frame.to_parquet(path, index=False)

    chunked, _, meta, _ = aggregate_dataset1_streaming(
        path=path,
        columns=DATASET1_COLUMN_CANDIDATES,
        batch_size=2,
        max_rows=None,
        thresholds_w_m2=[0, 5],
    )
    non_chunked = build_radiation_intervals(frame, thresholds_w_m2=[0, 5])

    chunked_main = chunked[chunked["threshold_w_m2"].eq(0.0)].sort_values("interval_start").reset_index(drop=True)
    non_chunked_main = non_chunked[non_chunked["threshold_w_m2"].eq(0.0)].sort_values("interval_start").reset_index(
        drop=True
    )

    assert chunked_main["radiation_phase"].tolist() == non_chunked_main["radiation_phase"].tolist()
    assert chunked[chunked["threshold_w_m2"].eq(5.0)]["radiation_phase"].tolist() == ["night", "night"]
    assert meta["chunk_aggregation_used"] is True
    assert meta["rows_processed_fraction"] == 1.0


def test_dataset3_size_guard_records_small_full_read_reason() -> None:
    metadata = _dataset3_size_guard(
        {"total_rows": 252, "rows_processed": 252, "row_limit_applied": False},
        max_full_rows_without_limit=2_000_000,
        mode="production",
    )

    assert metadata["dataset3_total_rows"] == 252
    assert metadata["dataset3_rows_processed"] == 252
    assert metadata["dataset3_size_guard_passed"] is True
    assert metadata["dataset3_full_in_memory_allowed_reason"] == "small_dataset3_within_max_full_rows_without_limit"


def test_dataset3_size_guard_fails_before_large_production_full_read(tmp_path: Path) -> None:
    path = tmp_path / "dataset3.parquet"
    pd.DataFrame({"loadcell_id": [1, 2, 3]}).to_parquet(path, index=False)

    try:
        _assert_dataset3_size_guard_before_read(
            path=path,
            max_rows=None,
            max_full_rows_without_limit=2,
            mode="production",
        )
    except RuntimeError as exc:
        assert "before full read" in str(exc)
    else:  # pragma: no cover - keeps the assertion message explicit
        raise AssertionError("Expected Dataset3 pre-read size guard to fail.")
