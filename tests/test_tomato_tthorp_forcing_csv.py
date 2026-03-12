from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from stomatal_optimiaztion.domains.tomato.tthorp.models.tomato_legacy import iter_forcing_csv


def test_iter_forcing_csv_sorts_datetime_and_matches_legacy_dt_rules(tmp_path: Path) -> None:
    forcing_path = tmp_path / "forcing.csv"
    pd.DataFrame(
        {
            "datetime": [
                "2025-01-01T12:00:00",
                "2025-01-01T00:00:00",
                "2025-01-01T13:00:00",
            ],
            "T_air_C": [20.0, 19.0, 21.0],
            "PAR_umol": [300.0, 200.0, 100.0],
            "CO2_ppm": [420.0, 420.0, 420.0],
            "RH_percent": [70.0, 70.0, 70.0],
            "wind_speed_ms": [1.0, 1.0, 1.0],
        }
    ).to_csv(forcing_path, index=False)

    steps = list(iter_forcing_csv(forcing_path, max_steps=10))

    assert len(steps) == 3
    assert steps[0].t.isoformat() == "2025-01-01T00:00:00"
    assert steps[1].t.isoformat() == "2025-01-01T12:00:00"
    assert steps[2].t.isoformat() == "2025-01-01T13:00:00"
    assert steps[0].dt_s == 21600.0
    assert steps[1].dt_s == 43200.0
    assert steps[2].dt_s == 3600.0


def test_iter_forcing_csv_raises_when_required_columns_missing(tmp_path: Path) -> None:
    forcing_path = tmp_path / "forcing.csv"
    pd.DataFrame(
        {
            "datetime": ["2025-01-01T00:00:00"],
            "T_air_C": [20.0],
            "PAR_umol": [250.0],
            "CO2_ppm": [420.0],
            "RH_percent": [65.0],
        }
    ).to_csv(forcing_path, index=False)

    with pytest.raises(ValueError, match="Missing required columns"):
        list(iter_forcing_csv(forcing_path))


def test_iter_forcing_csv_reconstructs_alias_columns_and_defaults(tmp_path: Path) -> None:
    forcing_path = tmp_path / "forcing_alias.csv"
    pd.DataFrame(
        {
            "Datetime": ["2025-01-01T00:00:00"],
            "t_a": [22.5],
            "co2_ppm": [None],
            "rh": [0.65],
            "u10": [2.0],
            "r_incom_w_m2": [100.0],
            "t_rad_c": [24.0],
        }
    ).to_csv(forcing_path, index=False)

    steps = list(
        iter_forcing_csv(
            forcing_path,
            default_co2_ppm=415.0,
            default_n_fruits_per_truss=5,
        )
    )

    assert len(steps) == 1
    step = steps[0]
    assert step.t.isoformat() == "2025-01-01T00:00:00"
    assert step.dt_s == 3600.0
    assert step.T_air_C == 22.5
    assert step.PAR_umol == pytest.approx(460.0)
    assert step.CO2_ppm == 415.0
    assert step.RH_percent == 65.0
    assert step.wind_speed_ms == 2.0
    assert step.SW_in_Wm2 == 100.0
    assert step.T_rad_C == 24.0
    assert step.n_fruits_per_truss == 5
