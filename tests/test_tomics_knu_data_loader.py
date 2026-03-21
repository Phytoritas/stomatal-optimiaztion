from __future__ import annotations

from pathlib import Path

from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation import (
    load_knu_validation_data,
)


def test_knu_loader_parses_sanitized_fixture_bundle() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    data = load_knu_validation_data(
        forcing_path=repo_root / "tests" / "fixtures" / "knu_sanitized" / "KNU_Tomato_Env_fixture.csv",
        yield_path=repo_root / "tests" / "fixtures" / "knu_sanitized" / "tomato_validation_data_yield_fixture.csv",
    )

    assert data.forcing_summary["rows"] >= 6
    assert data.forcing_summary["start"].startswith("2024-08-08T00:00:00")
    assert data.forcing_summary["end"].startswith("2024-08-11T18:00:00")
    assert int(data.forcing_summary["resolution_seconds_mode"]) == 21600
    assert data.yield_summary["rows"] == 4
    assert data.yield_summary["start"].startswith("2024-08-08T00:00:00")
    assert data.yield_summary["end"].startswith("2024-08-11T00:00:00")
    assert data.observation_unit_label == "g/m^2"
    assert data.measured_column == "Measured_Cumulative_Total_Fruit_DW (g/m^2)"
    assert data.estimated_column == "Estimated_Cumulative_Total_Fruit_DW (g/m^2)"
    assert float(data.yield_df[data.measured_column].iloc[0]) > 0.0
