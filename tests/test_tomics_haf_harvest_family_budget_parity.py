from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.haf_budget_parity import (
    build_haf_budget_parity_frame,
)
from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.haf_harvest_factorial import (
    build_haf_harvest_factorial_design,
)

from tests.tomics_haf_harvest_fixtures import synthetic_haf_harvest_config


def test_haf_budget_parity_counts_harvest_observation_and_latent_knobs(tmp_path) -> None:
    config = synthetic_haf_harvest_config(
        {
            "observer": tmp_path / "observer.csv",
            "observer_metadata": tmp_path / "observer.json",
            "latent": tmp_path / "latent.csv",
            "latent_metadata": tmp_path / "latent.json",
            "output_root": tmp_path / "out",
        }
    )
    design = build_haf_harvest_factorial_design(config)

    budget = build_haf_budget_parity_frame(design)

    assert budget["observation_operator_knobs_count"].eq(1).all()
    assert budget["harvest_knobs_count"].ge(0).all()
    latent_rows = budget[
        budget["allocator_family"].eq("tomics_haf_latent_allocation_research")
    ]
    assert latent_rows["latent_allocation_prior_knobs_count"].max() == 1
    assert budget["budget_parity_violation"].eq(False).all()


def test_haf_budget_parity_flags_extra_calibration_budget(tmp_path) -> None:
    config = synthetic_haf_harvest_config(
        {
            "observer": tmp_path / "observer.csv",
            "observer_metadata": tmp_path / "observer.json",
            "latent": tmp_path / "latent.csv",
            "latent_metadata": tmp_path / "latent.json",
            "output_root": tmp_path / "out",
        }
    )
    design = build_haf_harvest_factorial_design(config)
    design.loc[design.index[0], "extra_calibration_budget_units"] = 20

    budget = build_haf_budget_parity_frame(design)

    assert budget["budget_parity_violation"].any()
    assert budget["budget_penalty"].max() > 0.0
