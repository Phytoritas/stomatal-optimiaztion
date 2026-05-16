from pathlib import Path

import pandas as pd
import pytest

from stomatal_optimiaztion.domains.tomato.tomics.observers.parquet_streaming import (
    assert_no_large_full_load_without_limit,
    iter_projected_parquet_batches,
    parquet_metadata_summary,
    projected_columns,
    validate_production_row_cap_policy,
)


def test_projected_parquet_batches_and_metadata(tmp_path: Path) -> None:
    path = tmp_path / "data.parquet"
    pd.DataFrame({"timestamp": pd.date_range("2025-12-14", periods=5, freq="min"), "value": range(5)}).to_parquet(
        path,
        index=False,
    )

    meta = parquet_metadata_summary(path)
    batches = list(iter_projected_parquet_batches(path, ["timestamp", "missing"], batch_size=2))

    assert meta["total_rows"] == 5
    assert projected_columns(path, ["timestamp", "missing"]) == ["timestamp"]
    assert [batch.shape[0] for batch in batches] == [2, 2, 1]
    assert list(batches[0].columns) == ["timestamp"]


def test_large_full_load_guard_and_production_row_cap_policy() -> None:
    with pytest.raises(RuntimeError):
        assert_no_large_full_load_without_limit(
            total_rows=10,
            max_rows=None,
            mode="smoke",
            max_full_rows_without_limit=5,
        )

    assert_no_large_full_load_without_limit(
        total_rows=10,
        max_rows=None,
        mode="production",
        max_full_rows_without_limit=5,
    )

    with pytest.raises(ValueError):
        validate_production_row_cap_policy(
            mode="production",
            max_rows_by_dataset={"dataset1": 2, "dataset2": None},
            require_row_cap_absent_for_production=True,
        )
