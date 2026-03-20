from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import pandas.testing as pdt
import pytest

from stomatal_optimiaztion.domains.tomato.tomics.alloc import simulate
from stomatal_optimiaztion.domains.tomato.tomics.alloc.components.partitioning.fractions import (
    AllocationFractions,
)
from stomatal_optimiaztion.domains.tomato.tomics.alloc.components.partitioning.organ import Organ
from stomatal_optimiaztion.domains.tomato.tomics.alloc.models.tomato_legacy import (
    TomatoLegacyAdapter,
    TomatoModel,
    iter_forcing_csv,
)


def _forcing_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "datetime": [
                "2026-01-01T01:00:00",
                "2026-01-01T00:00:00",
                "2026-01-01T02:00:00",
            ],
            "T_air_C": [22.0, 21.0, 23.0],
            "PAR_umol": [300.0, 150.0, 450.0],
            "CO2_ppm": [420.0, 415.0, 430.0],
            "RH_percent": [65.0, 70.0, 60.0],
            "wind_speed_ms": [1.2, 0.8, 1.5],
        }
    )


def test_tomato_model_reset_state_preserves_legacy_defaults() -> None:
    model = TomatoModel()

    assert model.start_date == datetime(2021, 2, 23)
    assert model.current_date == model.start_date.date()
    assert model.W_lv == pytest.approx(50.0)
    assert model.W_st == pytest.approx(20.0)
    assert model.W_rt == pytest.approx(10.0)
    assert model.W_fr == pytest.approx(0.0)
    assert model.LAI == pytest.approx(model.W_lv * model.SLA)

    fixed_lai_model = TomatoModel(fixed_lai=2.4)
    assert fixed_lai_model.LAI == pytest.approx(2.4)


def test_tomato_model_load_input_data_and_update_inputs_match_legacy_surface(tmp_path: Path) -> None:
    csv_path = tmp_path / "forcing.csv"
    _forcing_frame().to_csv(csv_path, index=False)

    model = TomatoModel()
    loaded = model.load_input_data(csv_path)

    assert "n_fruits_per_truss" in loaded.columns
    assert loaded["n_fruits_per_truss"].tolist() == [4, 4, 4]

    model.update_inputs_from_row(loaded.iloc[0].to_dict())

    assert model.T_a == pytest.approx(22.0 + 273.15)
    assert model.u_PAR == pytest.approx(300.0)
    assert model.u_CO2 == pytest.approx(420.0)
    assert model.RH == pytest.approx(0.65)
    assert model.u == pytest.approx(1.2)
    assert model.n_f == 4
    assert model.T_rad_K == pytest.approx(model.T_a)
    assert model.SW_in_Wm2 == pytest.approx(model.u_PAR / model.W_TO_UMOL_CONVERSION / model.PAR_FRACTION_OF_SW)


def test_tomato_model_set_plant_density_updates_existing_cohort_multiplier() -> None:
    model = TomatoModel()
    model.truss_cohorts = [{"active": True, "mult": model.shoots_per_m2}]

    model.set_plant_density(plants_per_m2=2.0, shoots_per_plant=1.5)

    assert model.plants_per_m2 == pytest.approx(2.0)
    assert model.shoots_per_plant == pytest.approx(1.5)
    assert model.shoots_per_m2 == pytest.approx(3.0)
    assert model.truss_cohorts[0]["mult"] == pytest.approx(3.0)


def test_default_tomato_model_matches_adapter_path_on_same_forcing(tmp_path: Path) -> None:
    csv_path = tmp_path / "forcing.csv"
    _forcing_frame().to_csv(csv_path, index=False)

    model = TomatoModel()
    legacy_input = model.load_input_data(csv_path)
    legacy_out = model.run_simulation(legacy_input)

    forcing = iter_forcing_csv(csv_path, max_steps=3, default_dt_s=3600.0)
    adapter = TomatoLegacyAdapter()
    adapter_out = simulate(model=adapter, forcing=forcing, max_steps=3)

    assert len(legacy_out) == 3
    assert len(adapter_out) == 3

    legacy_dt = pd.Index(pd.to_datetime(legacy_out["datetime"]))
    adapter_dt = pd.Index(pd.to_datetime(adapter_out["datetime"]))
    pdt.assert_index_equal(adapter_dt, legacy_dt)

    for column in [
        "LAI",
        "T_canopy_C",
        "total_dry_weight_g_m2",
        "fruit_dry_weight_g_m2",
        "co2_flux_g_m2_s",
        "transpiration_rate_g_s_m2",
    ]:
        np.testing.assert_allclose(
            adapter_out[column].to_numpy(dtype=float),
            legacy_out[column].to_numpy(dtype=float),
            rtol=1e-9,
            atol=1e-9,
        )


def test_tomato_model_daily_boundary_creates_fr_based_cohort_from_queue() -> None:
    model = TomatoModel()
    model.queue_truss_n_f([6])
    model._truss_fraction_acc = 0.95
    model.daily_temp_accumulator = [(25.0 + 273.15, 24.0 * 3600.0)]

    model.update_daily_boundary(model.current_date + timedelta(days=1))

    assert model.truss_count == 1
    assert len(model.truss_cohorts) == 1
    assert model.truss_cohorts[0]["n_fruits"] == 6
    assert model.truss_cohorts[0]["mult"] == pytest.approx(model.shoots_per_m2)


def test_tomato_model_generative_sink_scales_with_shoot_density() -> None:
    model = TomatoModel()
    tdvs = float(model.pgr_params["c"]) + 0.5
    model.truss_cohorts = [
        {
            "tdvs": tdvs,
            "n_fruits": 4,
            "w_fr_cohort": 0.0,
            "active": True,
            "mult": model.shoots_per_m2,
        }
    ]

    base_sink = model._compute_generative_sink_absolute_gd()
    model.set_plant_density(shoots_per_m2=model.shoots_per_m2 * 2.0)
    doubled_sink = model._compute_generative_sink_absolute_gd()

    assert base_sink > 0.0
    assert doubled_sink == pytest.approx(base_sink * 2.0)


def test_tomato_model_water_stress_reduces_canopy_fluxes() -> None:
    base_row = {
        "T_air_C": 25.0,
        "PAR_umol": 650.0,
        "CO2_ppm": 420.0,
        "RH_percent": 60.0,
        "wind_speed_ms": 1.0,
        "n_fruits_per_truss": 4.0,
    }
    current_time = datetime(2026, 1, 1, 12, 0, 0)

    wet = TomatoModel()
    wet.theta_substrate = 0.50
    wet.update_inputs_from_row(base_row)
    wet.run_timestep_calculations(3600.0, current_time)
    wet_outputs = wet.get_current_outputs(current_time)

    dry = TomatoModel()
    dry.theta_substrate = 0.20
    dry.update_inputs_from_row(base_row)
    dry.run_timestep_calculations(3600.0, current_time)
    dry_outputs = dry.get_current_outputs(current_time)

    assert dry.water_supply_stress < wet.water_supply_stress
    assert dry.co2_flux_g_m2_s < wet.co2_flux_g_m2_s
    assert float(dry_outputs["transpiration_rate_g_s_m2"]) < float(wet_outputs["transpiration_rate_g_s_m2"])


def test_tomato_model_does_not_grow_under_zero_par() -> None:
    model = TomatoModel()
    model.update_inputs_from_row(
        {
            "T_air_C": 25.0,
            "PAR_umol": 0.0,
            "CO2_ppm": 420.0,
            "RH_percent": 60.0,
            "wind_speed_ms": 1.0,
            "n_fruits_per_truss": 4.0,
        }
    )

    model.run_timestep_calculations(3600.0, datetime(2026, 1, 1, 0, 0, 0))

    assert model.co2_flux_g_m2_s <= 0.0
    assert model.daily_dW_total == pytest.approx(0.0, abs=1e-12)
    assert model.W_lv == pytest.approx(50.0)
    assert model.W_st == pytest.approx(20.0)
    assert model.W_rt == pytest.approx(10.0)
    assert model.W_fr == pytest.approx(0.0)


def test_tomato_model_preserves_direct_fruit_growth_for_custom_policy() -> None:
    class _DirectFruitPolicy:
        name = "custom_direct_fruit"

        def compute(self, **_: object) -> AllocationFractions:
            return AllocationFractions(
                values={
                    Organ.FRUIT: 0.5,
                    Organ.LEAF: 0.25,
                    Organ.STEM: 0.15,
                    Organ.ROOT: 0.10,
                }
            )

    model = TomatoModel(partition_policy=_DirectFruitPolicy())
    model.update_inputs_from_row(
        {
            "T_air_C": 25.0,
            "PAR_umol": 600.0,
            "CO2_ppm": 420.0,
            "RH_percent": 60.0,
            "wind_speed_ms": 1.0,
            "n_fruits_per_truss": 4.0,
        }
    )

    model.run_timestep_calculations(3600.0, datetime(2026, 1, 1, 12, 0, 0))

    assert model.part_fruit == pytest.approx(0.5)
    assert model.W_fr > 0.0
