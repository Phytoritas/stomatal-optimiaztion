from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from stomatal_optimiaztion.domains.thorp.examples import (
    DEFAULT_LEGACY_THORP_EXAMPLE_DIR,
    build_allocation_fraction_frame,
    build_eco2_light_limited_frame,
    build_groundwater_sweep_frame,
    build_mass_fraction_frame,
    build_structural_trait_frame,
    render_thorp_example_figure_suite,
)

LEGACY_THORP_AVAILABLE = DEFAULT_LEGACY_THORP_EXAMPLE_DIR.exists()


def _script_path() -> Path:
    return Path(__file__).resolve().parents[1] / "scripts" / "render_thorp_example_figures.py"


@pytest.mark.skipif(not LEGACY_THORP_AVAILABLE, reason="legacy THORP example dir not available")
def test_build_thorp_example_frames_cover_expected_panels() -> None:
    mass_frame = build_mass_fraction_frame()
    allocation_frame = build_allocation_fraction_frame()
    structural_frame = build_structural_trait_frame()
    groundwater_frame = build_groundwater_sweep_frame()
    eco2_frame = build_eco2_light_limited_frame()

    assert set(mass_frame["panel_id"]) == {
        "lmf_absolute",
        "smf_absolute",
        "rmf_absolute",
        "lmf_difference",
        "smf_difference",
        "rmf_difference",
    }
    assert set(allocation_frame["panel_id"]) == {"leaf", "wood", "fine_root"}
    assert set(structural_frame["panel_id"]) == {
        "depth_time",
        "lai_time",
        "depth_mass",
        "lai_mass",
        "leaf_vs_sapwood",
        "huber_value",
    }
    assert set(groundwater_frame["panel_id"]) == {
        "depth_time",
        "depth_height",
        "gwtd_vs_root_depth",
        "deep_uptake_fraction",
        "rmf_height",
    }
    assert set(eco2_frame["panel_id"]) == {
        "lmf_absolute",
        "smf_absolute",
        "rmf_absolute",
        "lmf_difference",
        "smf_difference",
        "rmf_difference",
    }


@pytest.mark.skipif(not LEGACY_THORP_AVAILABLE, reason="legacy THORP example dir not available")
def test_render_thorp_example_suite_writes_outputs_and_matches_legacy_digest(tmp_path: Path) -> None:
    artifacts = render_thorp_example_figure_suite(output_dir=tmp_path)
    summary = artifacts.to_summary()

    for bundle_name in (
        "mass_fractions",
        "allocation_fractions",
        "structural_traits",
        "groundwater_sweep",
        "eco2_light_limited",
    ):
        metadata_path = Path(summary[bundle_name]["metadata"])
        png_path = Path(summary[bundle_name]["png"])
        pdf_path = Path(summary[bundle_name]["pdf"])
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))

        assert png_path.exists()
        assert pdf_path.exists()
        assert metadata["legacy_digest_summary"]["passed"] is True
        assert metadata["legacy_reference_image"]
        assert Path(metadata["legacy_reference_image"]).exists()


@pytest.mark.skipif(not LEGACY_THORP_AVAILABLE, reason="legacy THORP example dir not available")
def test_render_thorp_example_figures_script_entrypoint(tmp_path: Path) -> None:
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

    assert Path(summary["mass_fractions"]["png"]).exists()
    assert Path(summary["allocation_fractions"]["pdf"]).exists()
    assert Path(summary["groundwater_sweep"]["metadata"]).exists()
