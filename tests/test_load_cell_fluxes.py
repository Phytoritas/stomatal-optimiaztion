from __future__ import annotations

import pandas as pd
import pytest

from stomatal_optimiaztion.domains import load_cell
from stomatal_optimiaztion.domains.load_cell import compute_fluxes_per_second


def test_load_cell_import_surface_exposes_flux_helper() -> None:
    assert load_cell.compute_fluxes_per_second is compute_fluxes_per_second


def test_compute_fluxes_per_second_requires_expected_columns() -> None:
    with pytest.raises(KeyError, match="Missing required columns"):
        compute_fluxes_per_second(
            pd.DataFrame({"dW_smooth_kg_s": [0.0], "label": ["baseline"]})
        )


def test_compute_fluxes_per_second_splits_fluxes_and_preserves_balance() -> None:
    df = pd.DataFrame(
        {
            "dW_smooth_kg_s": [0.0, 0.4, -0.3, -0.2],
            "label": ["baseline", "irrigation", "drainage", "baseline"],
            "weight_smooth_kg": [10.0, 10.4, 10.1, 9.9],
        }
    )

    out = compute_fluxes_per_second(df, fix_water_balance=False)

    assert out["irrigation_kg_s"].tolist() == pytest.approx([0.0, 0.4, 0.0, 0.0])
    assert out["drainage_kg_s"].tolist() == pytest.approx([0.0, 0.0, 0.3, 0.0])
    assert out["transpiration_kg_s"].tolist() == pytest.approx([0.0, 0.0, 0.0, 0.2])
    assert out["cum_irrigation_kg"].tolist() == pytest.approx([0.0, 0.4, 0.4, 0.4])
    assert out["cum_drainage_kg"].tolist() == pytest.approx([0.0, 0.0, 0.3, 0.3])
    assert out["cum_transpiration_kg"].tolist() == pytest.approx(
        [0.0, 0.0, 0.0, 0.2]
    )
    assert out["reconstructed_weight_kg"].tolist() == pytest.approx(
        [10.0, 10.4, 10.1, 9.9]
    )
    assert out["water_balance_error_before_fix_kg"].tolist() == pytest.approx(
        [0.0, 0.0, 0.0, 0.0]
    )
    assert out["water_balance_error_kg"].tolist() == pytest.approx([0.0, 0.0, 0.0, 0.0])
    assert out["transpiration_scale"].tolist() == pytest.approx([1.0, 1.0, 1.0, 1.0])


def test_compute_fluxes_per_second_interpolates_transpiration_through_events() -> None:
    df = pd.DataFrame(
        {
            "dW_smooth_kg_s": [-0.1, 0.3, 0.3, -0.1],
            "label": ["baseline", "irrigation", "irrigation", "baseline"],
            "weight_smooth_kg": [10.0, 10.3, 10.6, 10.5],
        }
    )

    out = compute_fluxes_per_second(df, fix_water_balance=False)

    assert out["transpiration_kg_s"].tolist() == pytest.approx([0.1, 0.1, 0.1, 0.1])
    assert out["cum_transpiration_kg"].tolist() == pytest.approx([0.1, 0.2, 0.3, 0.4])


def test_compute_fluxes_per_second_can_disable_transpiration_interpolation() -> None:
    df = pd.DataFrame(
        {
            "dW_smooth_kg_s": [-0.1, 0.3, 0.3, -0.1],
            "label": ["baseline", "irrigation", "irrigation", "baseline"],
            "weight_smooth_kg": [10.0, 10.3, 10.6, 10.5],
        }
    )

    out = compute_fluxes_per_second(
        df,
        interpolate_transpiration_during_events=False,
        fix_water_balance=False,
    )

    assert out["transpiration_kg_s"].tolist() == pytest.approx([0.1, 0.0, 0.0, 0.1])


def test_compute_fluxes_per_second_clamps_upper_water_balance_scale() -> None:
    df = pd.DataFrame(
        {
            "dW_smooth_kg_s": [0.0, -0.1, -0.1],
            "label": ["baseline", "baseline", "baseline"],
            "weight_smooth_kg": [10.0, 9.85, 9.7],
        }
    )

    out = compute_fluxes_per_second(
        df,
        max_transpiration_scale=1.2,
    )

    assert out["water_balance_error_before_fix_kg"].iloc[-1] == pytest.approx(-0.1)
    assert out["transpiration_scale"].iloc[-1] == pytest.approx(1.2)
    assert out["transpiration_kg_s"].tolist() == pytest.approx([0.0, 0.12, 0.12])
    assert out["cum_transpiration_kg"].iloc[-1] == pytest.approx(0.24)
    assert out["water_balance_error_kg"].iloc[-1] == pytest.approx(-0.06)


def test_compute_fluxes_per_second_clamps_lower_water_balance_scale() -> None:
    df = pd.DataFrame(
        {
            "dW_smooth_kg_s": [0.0, -0.1, -0.1],
            "label": ["baseline", "baseline", "baseline"],
            "weight_smooth_kg": [10.0, 9.95, 9.95],
        }
    )

    out = compute_fluxes_per_second(
        df,
        min_transpiration_scale=0.5,
    )

    assert out["water_balance_error_before_fix_kg"].iloc[-1] == pytest.approx(0.15)
    assert out["transpiration_scale"].iloc[-1] == pytest.approx(0.5)
    assert out["transpiration_kg_s"].tolist() == pytest.approx([0.0, 0.05, 0.05])
    assert out["cum_transpiration_kg"].iloc[-1] == pytest.approx(0.1)
    assert out["water_balance_error_kg"].iloc[-1] == pytest.approx(0.05)
