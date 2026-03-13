from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from stomatal_optimiaztion.domains.tdgm.examples import (
    DEFAULT_LEGACY_TDGM_OFFLINE_DIR,
    DEFAULT_LEGACY_TDGM_THORP_G_DIR,
    build_max_height_for_soil_frame,
    build_phloem_transport_frame,
    build_poorter_smf_frame,
    build_source_vs_sink_growth_frame,
    build_thorp_g_growth_vs_carbon_frame,
    build_thorp_g_growth_vs_carbon_precipitation_frame,
    build_thorp_g_growth_vs_carbon_soil_moisture_detrended_frame,
    build_thorp_g_growth_vs_carbon_soil_moisture_frame,
    build_thorp_g_height_vs_age_turgor_threshold_frame,
    build_thorp_g_height_vs_age_waterstress_frame,
    build_thorp_g_soil_moisture_vs_carbon_frame,
    build_turgor_allocation_frame,
    build_turgor_growth_scaling_frame,
    build_turgor_water_potential_frame,
    render_tdgm_example_figure_suite,
)

LEGACY_TDGM_AVAILABLE = DEFAULT_LEGACY_TDGM_OFFLINE_DIR.exists() and DEFAULT_LEGACY_TDGM_THORP_G_DIR.exists()


def _script_path() -> Path:
    return Path(__file__).resolve().parents[1] / "scripts" / "render_tdgm_example_figures.py"


@pytest.mark.skipif(not LEGACY_TDGM_AVAILABLE, reason="legacy TDGM example dirs not available")
def test_build_tdgm_example_frames_cover_expected_panels() -> None:
    assert set(build_turgor_allocation_frame()["panel_id"]) == {"allocation_regression"}
    assert set(build_turgor_water_potential_frame()["panel_id"]) == {"predawn", "midday"}
    assert set(build_turgor_growth_scaling_frame()["panel_id"]) == {
        "growth_rate",
        "local_exponent",
        "regressed_exponent",
        "max_height",
    }
    assert set(build_max_height_for_soil_frame()["panel_id"]) == {
        "water_potential_vs_height",
        "max_height_vs_p_minus_pet",
    }
    assert set(build_poorter_smf_frame()["panel_id"]) == {"poorter_smf"}
    assert set(build_phloem_transport_frame(height_key="04m")["panel_id"]) == {"phloem_transport_04m"}
    assert set(build_phloem_transport_frame(height_key="44m")["panel_id"]) == {"phloem_transport_44m"}
    assert set(build_source_vs_sink_growth_frame()["panel_id"]) == {
        "ratio_over_age",
        "source_growth",
        "sink_growth",
    }
    assert set(build_thorp_g_growth_vs_carbon_frame()["panel_id"]) == {
        "instant_precipitation",
        "instant_relative_humidity",
        "instant_combined",
        "annual_precipitation",
        "annual_relative_humidity",
        "annual_combined",
    }
    assert set(build_thorp_g_growth_vs_carbon_precipitation_frame()["panel_id"]) == {"control", "rh_80"}
    assert set(build_thorp_g_growth_vs_carbon_soil_moisture_frame()["panel_id"]) == {"control", "rh_80"}
    assert set(build_thorp_g_growth_vs_carbon_soil_moisture_detrended_frame()["panel_id"]) == {"control", "rh_80"}
    assert set(build_thorp_g_soil_moisture_vs_carbon_frame()["panel_id"]) == {"control", "rh_80"}
    assert set(build_thorp_g_height_vs_age_turgor_threshold_frame()["panel_id"]) == {"height_vs_age"}
    assert set(build_thorp_g_height_vs_age_waterstress_frame()["panel_id"]) == {
        "precipitation",
        "relative_humidity",
        "combined",
    }


@pytest.mark.skipif(not LEGACY_TDGM_AVAILABLE, reason="legacy TDGM example dirs not available")
def test_render_tdgm_example_suite_writes_outputs_and_matches_legacy_digest(tmp_path: Path) -> None:
    artifacts = render_tdgm_example_figure_suite(output_dir=tmp_path)
    summary = artifacts.to_summary()
    for bundle_name in summary:
        metadata_path = Path(summary[bundle_name]["metadata"])
        png_path = Path(summary[bundle_name]["png"])
        pdf_path = Path(summary[bundle_name]["pdf"])
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        assert png_path.exists()
        assert pdf_path.exists()
        assert Path(metadata["legacy_reference_script"]).exists()
        assert metadata["legacy_digest_summary"]["passed"] is True


@pytest.mark.skipif(not LEGACY_TDGM_AVAILABLE, reason="legacy TDGM example dirs not available")
def test_render_tdgm_example_figures_script_entrypoint(tmp_path: Path) -> None:
    result = subprocess.run(
        [
            sys.executable,
            str(_script_path()),
            "--output-dir",
            str(tmp_path / "rendered"),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    summary = json.loads(result.stdout)
    assert Path(summary["turgor_allocation"]["png"]).exists()
    assert Path(summary["max_height_for_soil"]["pdf"]).exists()
    assert Path(summary["source_vs_sink_growth"]["metadata"]).exists()
    assert Path(summary["thorp_g_growth_vs_carbon"]["png"]).exists()
    assert Path(summary["thorp_g_height_vs_age_turgor_threshold"]["metadata"]).exists()
