from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from stomatal_optimiaztion.domains.gosm.examples import (
    build_manuscript_panel_frame,
    render_manuscript_panel_bundle,
)


def _script_path() -> Path:
    return Path(__file__).resolve().parents[1] / "scripts" / "render_gosm_manuscript_panels.py"


def test_build_manuscript_panel_frame_contains_expected_panels() -> None:
    frame = build_manuscript_panel_frame()

    assert set(frame["panel_group"]) == {"vulnerability", "photosynthesis", "growth"}
    assert set(frame["panel_id"]) == {
        "vulnerability_root",
        "vulnerability_stem",
        "vulnerability_leaf",
        "photosynthesis_an_gc",
        "photosynthesis_an_ci",
        "growth_rm_c",
        "growth_g_c",
        "growth_g_ta",
        "growth_g_e",
    }


def test_render_manuscript_panel_bundle_writes_outputs(tmp_path: Path) -> None:
    artifacts = render_manuscript_panel_bundle(output_dir=tmp_path)
    metadata = json.loads(artifacts.metadata_path.read_text(encoding="utf-8"))

    assert artifacts.data_csv_path.exists()
    assert artifacts.manifest_csv_path.exists()
    assert artifacts.overview_png_path.exists()
    assert artifacts.overview_pdf_path.exists()
    assert len(list(artifacts.panel_dir.glob("*.png"))) == 9
    assert metadata["legacy_digest_summary"]["overall_passed"] is True


def test_render_gosm_manuscript_panels_script_entrypoint(tmp_path: Path) -> None:
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

    assert Path(summary["overview_png"]).exists()
    assert Path(summary["manifest_csv"]).exists()
