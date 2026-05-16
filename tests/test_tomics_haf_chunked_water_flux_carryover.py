from pathlib import Path

import pandas as pd
import pytest

from stomatal_optimiaztion.domains.tomato.tomics.observers.contracts import DATASET1_COLUMN_CANDIDATES
from stomatal_optimiaztion.domains.tomato.tomics.observers.production_export import (
    aggregate_dataset1_streaming,
)


def test_chunked_water_flux_carryover_across_batches_and_groups(tmp_path: Path) -> None:
    frame = pd.DataFrame(
        {
            "timestamp": pd.to_datetime(
                [
                    "2025-12-14 00:00:00",
                    "2025-12-14 00:05:00",
                    "2025-12-14 00:10:00",
                    "2025-12-14 00:00:00",
                    "2025-12-14 00:05:00",
                ]
            ),
            "date": ["2025-12-14"] * 5,
            "loadcell_id": [1, 1, 1, 4, 4],
            "sample_id": [1, 1, 1, 4, 4],
            "treatment": ["Control", "Control", "Control", "Drought", "Drought"],
            "loadcell_weight_kg": [10.0, 9.99, 9.98, 20.0, 19.99],
            "env_inside_radiation_wm2": [0, 1, 2, 0, 1],
        }
    ).sort_values(["loadcell_id", "timestamp"])
    path = tmp_path / "dataset1.parquet"
    frame.to_parquet(path, index=False)

    _, water, meta, _ = aggregate_dataset1_streaming(
        path=path,
        columns=DATASET1_COLUMN_CANDIDATES,
        batch_size=2,
        max_rows=None,
        event_threshold_g=5,
    )

    control_loss = water[water["loadcell_id"].eq(1)]["loss_g_10min_unscaled"].sum()
    drought_loss = water[water["loadcell_id"].eq(4)]["loss_g_10min_unscaled"].sum()

    assert control_loss == pytest.approx(20.0)
    assert drought_loss == pytest.approx(10.0)
    assert water["event_flag"].any()
    assert meta["water_flux_chunk_carryover_used"] is True
