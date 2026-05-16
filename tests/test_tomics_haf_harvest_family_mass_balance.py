from pathlib import Path

import pandas as pd

from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.haf_harvest_factorial import (
    run_tomics_haf_harvest_family_factorial,
)

from tests.tomics_haf_harvest_fixtures import (
    synthetic_haf_harvest_config,
    write_synthetic_haf_harvest_inputs,
)


def test_haf_harvest_mass_balance_output_is_finite_and_unpenalized(tmp_path: Path) -> None:
    paths = write_synthetic_haf_harvest_inputs(tmp_path)
    result = run_tomics_haf_harvest_family_factorial(
        synthetic_haf_harvest_config(paths),
        repo_root=tmp_path,
        config_path=tmp_path / "config.yaml",
    )

    mass_balance = pd.read_csv(result["paths"]["mass_balance"])

    assert not mass_balance.empty
    assert mass_balance["mass_balance_error"].max() == 0.0
    assert mass_balance["leaf_harvest_mass_balance_error"].max() == 0.0
    assert mass_balance["invalid_run_flag"].eq(False).all()
