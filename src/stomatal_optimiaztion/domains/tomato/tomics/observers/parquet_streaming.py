from __future__ import annotations

from collections.abc import Iterator, Sequence
from pathlib import Path
from typing import Any

import pandas as pd


def parquet_metadata_summary(path: str | Path) -> dict[str, Any]:
    import pyarrow.parquet as pq

    parquet_path = Path(path)
    parquet_file = pq.ParquetFile(parquet_path)
    return {
        "path": str(parquet_path),
        "file_size_bytes": parquet_path.stat().st_size,
        "total_rows": int(parquet_file.metadata.num_rows),
        "row_group_count": int(parquet_file.metadata.num_row_groups),
        "columns": [str(name) for name in parquet_file.schema_arrow.names],
    }


def projected_columns(path: str | Path, columns: Sequence[str]) -> list[str]:
    import pyarrow.parquet as pq

    parquet_file = pq.ParquetFile(path)
    available = set(parquet_file.schema_arrow.names)
    return [str(column) for column in columns if column in available]


def iter_projected_parquet_batches(
    path: str | Path,
    columns: Sequence[str],
    *,
    batch_size: int,
    max_rows: int | None = None,
) -> Iterator[pd.DataFrame]:
    import pyarrow.parquet as pq

    parquet_file = pq.ParquetFile(path)
    available = projected_columns(path, columns)
    remaining = max_rows
    for batch in parquet_file.iter_batches(batch_size=batch_size, columns=available):
        frame = batch.to_pandas()
        if remaining is not None:
            if remaining <= 0:
                break
            if frame.shape[0] > remaining:
                frame = frame.iloc[:remaining].copy()
            remaining -= int(frame.shape[0])
        yield frame


def assert_no_large_full_load_without_limit(
    *,
    total_rows: int,
    max_rows: int | None,
    mode: str,
    max_full_rows_without_limit: int,
    fail_on_full_in_memory_large_dataset: bool = True,
) -> None:
    if mode == "production":
        return
    if fail_on_full_in_memory_large_dataset and max_rows is None and total_rows > max_full_rows_without_limit:
        raise RuntimeError(
            f"Refusing full in-memory load of {total_rows:,} rows in {mode!r} mode. "
            "Set max_rows for smoke mode or use production chunk aggregation."
        )


def validate_production_row_cap_policy(
    *,
    mode: str,
    max_rows_by_dataset: dict[str, Any],
    require_row_cap_absent_for_production: bool,
) -> None:
    if mode != "production" or not require_row_cap_absent_for_production:
        return
    capped = {
        dataset: value
        for dataset, value in max_rows_by_dataset.items()
        if value is not None
    }
    if capped:
        raise ValueError(f"Production mode forbids row caps, got {capped}.")

