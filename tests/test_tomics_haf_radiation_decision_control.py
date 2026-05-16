import pytest

from stomatal_optimiaztion.domains.tomato.tomics.observers.pipeline import _radiation_column_for_pipeline


def test_pipeline_accepts_dataset1_radiation_selected_for_10min_daynight() -> None:
    assert (
        _radiation_column_for_pipeline(
            {
                "radiation_daynight_primary_source": "dataset1",
                "radiation_column_used": "env_inside_radiation_wm2",
                "selected_for_daynight_10min": True,
            }
        )
        == "env_inside_radiation_wm2"
    )


def test_pipeline_rejects_daily_only_radiation_for_10min_daynight() -> None:
    with pytest.raises(RuntimeError, match="No radiation source is selected"):
        _radiation_column_for_pipeline(
            {
                "radiation_daynight_primary_source": "",
                "radiation_column_used": "",
                "selected_for_daynight_10min": False,
                "selected_for_daily_summary_only": True,
            }
        )


def test_pipeline_rejects_non_dataset1_primary_for_canonical_observer_export() -> None:
    with pytest.raises(RuntimeError, match="requires Dataset1 radiation"):
        _radiation_column_for_pipeline(
            {
                "radiation_daynight_primary_source": "fruit_leaf_temperature_solar_raw_dat",
                "radiation_column_used": "SolarRad_Avg",
                "selected_for_daynight_10min": True,
            }
        )
