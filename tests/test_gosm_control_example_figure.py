from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

from stomatal_optimiaztion.domains.gosm.examples import (
    build_control_example_payload,
    legacy_control_digest_summary,
    render_control_example_figure_bundle,
)


def _script_path() -> Path:
    return Path(__file__).resolve().parents[1] / "scripts" / "render_gosm_control_example.py"


def _load_script_module():
    spec = importlib.util.spec_from_file_location("render_gosm_control_example_script", _script_path())
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load render_gosm_control_example.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_control_payload_matches_legacy_digests() -> None:
    payload = build_control_example_payload()
    digest_summary = legacy_control_digest_summary(payload)

    assert digest_summary["passed"] is True
    assert payload.g_c_opt == pytest.approx(0.056688071689628)
    assert payload.x_limit_max == pytest.approx(0.3)


def test_render_control_example_bundle_writes_expected_artifacts(tmp_path: Path) -> None:
    artifacts = render_control_example_figure_bundle(output_dir=tmp_path)
    metadata = json.loads(artifacts.metadata_path.read_text(encoding="utf-8"))

    assert artifacts.data_csv_path.exists()
    assert artifacts.spec_copy_path.exists()
    assert artifacts.resolved_spec_path.exists()
    assert artifacts.tokens_copy_path.exists()
    assert artifacts.png_path.exists()
    assert artifacts.pdf_path.exists()
    assert metadata["legacy_digest_summary"]["passed"] is True


def test_render_control_example_script_entrypoint(tmp_path: Path) -> None:
    script = _script_path()
    result = subprocess.run(
        [sys.executable, str(script), "--output-dir", str(tmp_path)],
        check=True,
        capture_output=True,
        text=True,
    )
    summary = json.loads(result.stdout)

    assert Path(summary["png"]).exists()
    assert Path(summary["pdf"]).exists()
    assert Path(summary["metadata"]).exists()


def test_build_parser_defaults_to_repo_bundle_paths() -> None:
    module = _load_script_module()
    parser = module.build_parser()
    args = parser.parse_args([])

    assert args.output_dir.name == "control_example"
    assert args.spec.name == "control_example_figure.yaml"
