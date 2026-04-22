from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation import (
    run_current_vs_promoted_factorial,
)

pytestmark = pytest.mark.slow


def _write_public_config(tmp_path: Path, *, repo_root: Path, source_config: str) -> Path:
    source_path = repo_root / source_config
    config = yaml.safe_load(source_path.read_text(encoding="utf-8"))
    config["paths"]["repo_root"] = str(repo_root)
    validation = config["validation"]
    validation["private_data_contract_path"] = str((repo_root / validation["private_data_contract_path"]).resolve())
    validation["forcing_csv_path"] = str((repo_root / validation["forcing_csv_path"]).resolve())
    validation["yield_xlsx_path"] = str((repo_root / validation["yield_xlsx_path"]).resolve())
    validation["prepared_output_root"] = str(tmp_path / config["exp"]["name"] / "prepared")
    paths = config["paths"]
    paths["current_output_root"] = str(tmp_path / config["exp"]["name"] / "current-factorial")
    paths["promoted_output_root"] = str(tmp_path / config["exp"]["name"] / "promoted-factorial")
    paths["comparison_output_root"] = str(tmp_path / config["exp"]["name"] / "comparison")
    for key, value in config.get("plots", {}).items():
        config["plots"][key] = str((repo_root / value).resolve())
    out_path = tmp_path / f"{config['exp']['name']}.yaml"
    out_path.write_text(yaml.safe_dump(config, sort_keys=False, allow_unicode=False), encoding="utf-8")
    return out_path


@pytest.mark.parametrize(
    "source_config",
    [
        "configs/exp/tomics_current_vs_promoted_factorial_public_rda_2018_farm10_season1.yaml",
        "configs/exp/tomics_current_vs_promoted_factorial_public_ai_competition_2023_farmKRKW000001.yaml",
    ],
)
def test_public_current_factorial_runner_handles_sparse_observed_dates(
    tmp_path: Path,
    source_config: str,
) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    config_path = _write_public_config(tmp_path, repo_root=repo_root, source_config=source_config)

    summary = run_current_vs_promoted_factorial(config_path=config_path, mode="current")
    output_root = Path(summary["current"]["output_root"])

    assert (output_root / "candidate_ranking.csv").exists()
    assert (output_root / "selected_architecture.json").exists()
    assert (output_root / "validation_plots" / "yield_fit_overlay.png").exists()
