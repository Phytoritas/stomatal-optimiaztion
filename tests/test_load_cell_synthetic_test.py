from __future__ import annotations

import importlib
from pathlib import Path

from stomatal_optimiaztion.domains import load_cell
from stomatal_optimiaztion.domains.load_cell import generate_synthetic_dataset
from stomatal_optimiaztion.domains.load_cell import run_synthetic_pipeline

load_cell_synthetic_test = importlib.import_module(
    "stomatal_optimiaztion.domains.load_cell.synthetic_test"
)


def test_load_cell_import_surface_exposes_synthetic_harness() -> None:
    assert load_cell.generate_synthetic_dataset is generate_synthetic_dataset
    assert load_cell.run_synthetic_pipeline is run_synthetic_pipeline
    assert load_cell.synthetic_test_main is load_cell_synthetic_test.main


def test_generate_synthetic_dataset_is_deterministic() -> None:
    first_df, first_truth = load_cell_synthetic_test.generate_synthetic_dataset()
    second_df, second_truth = load_cell_synthetic_test.generate_synthetic_dataset()

    assert first_truth == {
        "irrigation_kg": 2.1,
        "drainage_kg": 4.32,
        "transpiration_kg": 2.1599,
    }
    assert first_df.equals(second_df)
    assert first_truth == second_truth
    assert list(first_df.columns) == ["timestamp", "weight_kg"]
    assert len(first_df) == 21600


def test_run_synthetic_pipeline_returns_small_errors(tmp_path: Path, capsys) -> None:
    result = load_cell_synthetic_test.run_synthetic_pipeline(tmp_path / "synthetic")

    captured = capsys.readouterr()
    assert "Synthetic test passed." in captured.out
    assert set(result) == {"truth", "estimates", "errors"}
    assert abs(result["errors"]["irrigation_kg"]) <= 0.05
    assert abs(result["errors"]["drainage_kg"]) <= 0.05
    assert abs(result["errors"]["transpiration_kg"]) <= 0.02
    assert (tmp_path / "synthetic" / "synthetic_loadcell.csv").exists()


def test_main_runs_with_legacy_default_style_output_dir(tmp_path: Path) -> None:
    result = load_cell_synthetic_test.main(tmp_path / "synthetic-output")

    assert result == 0
    assert (tmp_path / "synthetic-output" / "synthetic_loadcell.csv").exists()
