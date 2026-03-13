from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from stomatal_optimiaztion.domains.gosm.examples import (
    DEFAULT_LEGACY_GOSM_EXAMPLE_DIR,
    render_rerun_parity_suite as render_gosm_rerun_parity_suite,
)
from stomatal_optimiaztion.domains.tdgm.examples import (
    DEFAULT_LEGACY_TDGM_THORP_G_DIR,
    render_rerun_parity_suite as render_tdgm_rerun_parity_suite,
)
from stomatal_optimiaztion.domains.thorp.examples import (
    DEFAULT_RERUN_PARITY_LEGACY_MAT_PATH,
    render_rerun_parity_bundle as render_thorp_rerun_parity_bundle,
)


def _script_path() -> Path:
    return Path(__file__).resolve().parents[1] / "scripts" / "render_root_rerun_parity_figures.py"


def _max_abs_diff(frame: pd.DataFrame, *, group_columns: list[str], sort_by: str, value_column: str) -> float:
    max_diff = 0.0
    for _, group in frame.groupby(group_columns, dropna=False):
        legacy = group[group["source"] == "legacy"].sort_values(sort_by)[value_column].to_numpy(dtype=float)
        python = group[group["source"] == "python"].sort_values(sort_by)[value_column].to_numpy(dtype=float)
        assert legacy.shape == python.shape
        if legacy.size:
            max_diff = max(max_diff, float(np.max(np.abs(python - legacy))))
    return max_diff


def _max_abs_diff_from_diff(frame: pd.DataFrame, *, count: int | None = None) -> float:
    values = frame["abs_diff"].to_numpy(dtype=float)
    if count is not None:
        values = values[:count]
    values = values[np.isfinite(values)]
    return float(np.max(values)) if values.size else 0.0


@pytest.mark.skipif(not DEFAULT_RERUN_PARITY_LEGACY_MAT_PATH.exists(), reason="legacy THORP rerun MAT not available")
def test_render_thorp_rerun_parity_bundle_writes_outputs(tmp_path: Path) -> None:
    artifacts = render_thorp_rerun_parity_bundle(output_dir=tmp_path / "thorp", max_steps=60)
    assert artifacts.python_csv_path is not None
    assert artifacts.legacy_csv_path is not None
    assert artifacts.diff_csv_path is not None
    frame = pd.read_csv(artifacts.diff_csv_path)

    assert artifacts.png_path.exists()
    assert artifacts.spec_copy_path is None
    assert artifacts.metadata_path is None
    assert _max_abs_diff_from_diff(frame[frame["panel_id"] == "height"], count=3) == pytest.approx(0.0)
    assert _max_abs_diff_from_diff(frame[frame["panel_id"] == "assimilation"], count=3) == pytest.approx(0.0)


@pytest.mark.skipif(not DEFAULT_LEGACY_GOSM_EXAMPLE_DIR.exists(), reason="legacy GOSM rerun MATs not available")
def test_render_gosm_rerun_parity_suite_writes_outputs(tmp_path: Path) -> None:
    artifacts = render_gosm_rerun_parity_suite(output_dir=tmp_path / "gosm")
    summary = artifacts.to_summary()
    control_frame = pd.read_csv(Path(summary["control"]["diff_csv"]))
    rh_frame = pd.read_csv(Path(summary["rh"]["diff_csv"]))

    assert Path(summary["control"]["png"]).exists()
    assert Path(summary["p_soil_min_true"]["diff_csv"]).exists()
    assert summary["p_soil_min_imag"] is None
    assert "metadata" not in summary["control"]
    assert _max_abs_diff_from_diff(control_frame[control_frame["series_key"] == "g0_umol_c_s"]) < 1e-8
    assert _max_abs_diff_from_diff(rh_frame[rh_frame["panel_id"] == "g_c_steady_state"]) < 1e-8


@pytest.mark.skipif(not DEFAULT_LEGACY_TDGM_THORP_G_DIR.exists(), reason="legacy TDGM THORP-G MATs not available")
def test_render_tdgm_rerun_parity_suite_can_filter_cases(tmp_path: Path) -> None:
    artifacts = render_tdgm_rerun_parity_suite(
        output_dir=tmp_path / "tdgm",
        case_names=["THORP_data_Control_Turgor.mat"],
        max_steps=60,
    )
    summary = artifacts.to_summary()
    assert set(summary) == {"thorp_data_control_turgor"}
    assert Path(summary["thorp_data_control_turgor"]["png"]).exists()
    frame = pd.read_csv(Path(summary["thorp_data_control_turgor"]["diff_csv"]))
    assert _max_abs_diff_from_diff(frame[frame["panel_id"] == "height"], count=3) == pytest.approx(0.0)


@pytest.mark.skipif(
    not (
        DEFAULT_RERUN_PARITY_LEGACY_MAT_PATH.exists()
        and DEFAULT_LEGACY_GOSM_EXAMPLE_DIR.exists()
        and DEFAULT_LEGACY_TDGM_THORP_G_DIR.exists()
    ),
    reason="legacy rerun parity sources not available",
)
def test_render_root_rerun_parity_figures_script_entrypoint(tmp_path: Path) -> None:
    result = subprocess.run(
        [
            sys.executable,
            str(_script_path()),
            "--output-dir",
            str(tmp_path / "rendered"),
            "--fast-smoke",
            "--tdgm-case",
            "THORP_data_Control_Turgor.mat",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    summary = json.loads(result.stdout)
    assert Path(summary["thorp"]["png"]).exists()
    assert Path(summary["gosm"]["control"]["diff_csv"]).exists()
    assert Path(summary["tdgm"]["thorp_data_control_turgor"]["png"]).exists()
