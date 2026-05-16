from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.haf_harvest_factorial import (
    build_haf_harvest_factorial_design,
)

from tests.tomics_haf_harvest_fixtures import synthetic_haf_harvest_config


def test_haf_harvest_design_is_staged_and_blocks_forbidden_fdmc(tmp_path) -> None:
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

    assert {"HF0", "HF1", "HF2", "HF3"}.issubset(set(design["stage"]))
    assert "HF5" not in set(design["stage"])
    assert set(design["fdmc_mode"]) == {"constant_0p056"}
    assert "constant_0p065" not in set(design["fdmc_mode"])
    assert "dmc_sensitivity" not in set(design["fdmc_mode"])
    assert "tomsim_truss_incumbent" in set(design["fruit_harvest_family"])
    assert "dekoning_fds_ripe" in set(design["fruit_harvest_family"])
    assert design["run_final_promotion_gate"].eq(False).all()
    assert design["raw_THORP_allocator_used"].eq(False).all()
