from __future__ import annotations

from pathlib import Path

import pandas as pd

from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation import (
    apply_theta_substrate_proxy,
    read_knu_forcing_csv,
)


def _forcing_head() -> pd.DataFrame:
    repo_root = Path(__file__).resolve().parents[1]
    forcing = read_knu_forcing_csv(repo_root / "tests" / "fixtures" / "knu_sanitized" / "KNU_Tomato_Env_fixture.csv")
    return forcing.copy()


def test_theta_proxy_modes_stay_within_greenhouse_bounds() -> None:
    forcing = _forcing_head()

    flat = apply_theta_substrate_proxy(forcing, mode="flat_constant", scenario="moderate")
    bucket = apply_theta_substrate_proxy(forcing, mode="bucket_irrigated", scenario="moderate")
    hysteretic = apply_theta_substrate_proxy(forcing, mode="bucket_irrigated_hysteretic", scenario="wet")

    for frame in (flat, bucket, hysteretic):
        assert frame["theta_substrate"].between(0.40, 0.85).all()
        assert frame["rootzone_multistress"].between(0.0, 1.0).all()
        assert frame["rootzone_saturation"].between(0.0, 1.0).all()

    assert flat["theta_substrate"].nunique() == 1
    assert bucket["theta_substrate"].nunique() > 1
    assert hysteretic["theta_substrate"].mean() >= bucket["theta_substrate"].mean()
