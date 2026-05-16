from pathlib import Path

import json

from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.haf_budget_parity import (
    BUDGET_PARITY_BASIS,
    BUDGET_PARITY_LIMITATIONS,
    build_haf_budget_parity_frame,
)
from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.haf_harvest_factorial import (
    build_haf_harvest_factorial_design,
    run_tomics_haf_harvest_family_factorial,
)

from tests.tomics_haf_harvest_fixtures import (
    synthetic_haf_harvest_config,
    write_synthetic_haf_harvest_inputs,
)


def test_budget_parity_limitations_are_explicit_in_budget_frame(tmp_path: Path) -> None:
    config = synthetic_haf_harvest_config(
        {
            "observer": tmp_path / "observer.csv",
            "observer_metadata": tmp_path / "observer.json",
            "latent": tmp_path / "latent.csv",
            "latent_metadata": tmp_path / "latent.json",
            "output_root": tmp_path / "out",
        }
    )
    budget = build_haf_budget_parity_frame(build_haf_harvest_factorial_design(config))

    assert budget["budget_parity_basis"].eq(BUDGET_PARITY_BASIS).all()
    assert budget["wall_clock_compute_budget_parity_evaluated"].eq(False).all()
    assert budget["wall_clock_compute_budget_parity_required_for_goal_3b"].eq(False).all()
    assert budget["budget_parity_limitations"].str.contains("not").all()


def test_budget_parity_limitations_are_explicit_in_metadata(tmp_path: Path) -> None:
    paths = write_synthetic_haf_harvest_inputs(tmp_path)
    result = run_tomics_haf_harvest_family_factorial(
        synthetic_haf_harvest_config(paths),
        repo_root=tmp_path,
        config_path=tmp_path / "config.yaml",
    )
    metadata = json.loads(Path(result["paths"]["metadata"]).read_text(encoding="utf-8"))

    assert metadata["budget_parity_basis"] == BUDGET_PARITY_BASIS
    assert metadata["wall_clock_compute_budget_parity_evaluated"] is False
    assert metadata["wall_clock_compute_budget_parity_required_for_goal_3b"] is False
    assert metadata["budget_parity_limitations"] == BUDGET_PARITY_LIMITATIONS
