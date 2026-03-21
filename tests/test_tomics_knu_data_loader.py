from __future__ import annotations

from pathlib import Path

from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation import (
    load_knu_validation_data,
)


def test_knu_loader_parses_expected_actual_data_files() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    data = load_knu_validation_data(
        forcing_path=repo_root / "data" / "forcing" / "KNU_Tomato_Env.CSV",
        yield_path=repo_root / "data" / "forcing" / "tomato_validation_data_yield_260222.xlsx",
    )

    assert data.forcing_summary["rows"] == 116640
    assert data.forcing_summary["start"].startswith("2024-06-13T00:00:00")
    assert data.forcing_summary["end"].startswith("2024-08-31T23:59:00")
    assert int(data.forcing_summary["resolution_seconds_mode"]) == 60
    assert data.yield_summary["rows"] == 24
    assert data.yield_summary["start"].startswith("2024-08-08T00:00:00")
    assert data.yield_summary["end"].startswith("2024-08-31T00:00:00")
    assert data.observation_unit_label == "g/m^2"
    assert data.measured_column == "Measured_Cumulative_Total_Fruit_DW (g/m^2)"
    assert data.estimated_column == "Estimated_Cumulative_Total_Fruit_DW (g/m^2)"
    assert float(data.yield_df[data.measured_column].iloc[0]) > 0.0
