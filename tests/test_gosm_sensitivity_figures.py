from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
from scipy.io import savemat

from stomatal_optimiaztion.domains.gosm.examples import (
    build_compare_true_vs_imag_frame,
    build_sensitivity_all_frame,
    build_sensitivity_some_frame,
    load_sensitivity_scenario,
    render_sensitivity_figure_suite,
)


def _script_path() -> Path:
    return Path(__file__).resolve().parents[1] / "scripts" / "render_gosm_sensitivity_figures.py"


def _load_script_module():
    spec = importlib.util.spec_from_file_location("render_gosm_sensitivity_figures_script", _script_path())
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load render_gosm_sensitivity_figures.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _study_legend_array() -> np.ndarray:
    labels = [
        "Cowan & Farquhar (1977)",
        "Prentice et al. (2014)",
        "Sperry et al. (2017)",
        "Anderegg et al. (2018)",
        "Dewar et al. (2018)",
        "Eller et al. (2018)",
        "Wang et al. (2020)",
    ]
    array = np.empty((len(labels), 1), dtype=object)
    for idx, label in enumerate(labels):
        array[idx, 0] = label
    return array


def _write_sensitivity_mat(directory: Path, *, filename: str, param: str, n_points: int, offset: float) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    param_values = {
        "RH": np.linspace(0.8, 2.2, n_points),
        "c_a": np.linspace(0.00035, 0.0006, n_points),
        "P_soil": np.linspace(-0.8, 0.0, n_points),
        "P_soil_min": np.linspace(-2.0, -0.2, n_points),
    }[param]
    param_test = param_values.reshape(1, -1)
    vpd_ss = np.linspace(0.8, 2.2, n_points).reshape(1, -1)
    vpd_in = np.vstack([vpd_ss + 0.02 * idx for idx in range(6)])
    vpd_study = np.vstack([vpd_ss + 0.01 * idx for idx in range(7)])

    g_c_ss = np.linspace(0.05, 0.12, n_points).reshape(1, -1) + offset
    g_c_in = np.vstack([g_c_ss + 0.005 * idx for idx in range(6)])
    g_c_study = np.vstack([g_c_ss + 0.003 * idx for idx in range(7)])
    lambda_ss = np.linspace(3e-4, 8e-3, n_points).reshape(1, -1) * (1 + offset)
    lambda_in = np.vstack([lambda_ss * (1 + 0.05 * idx) for idx in range(6)])
    lambda_study = np.vstack([lambda_ss * (1 + 0.04 * idx) for idx in range(7)])
    g_ss = np.linspace(1.0, 8.0, n_points).reshape(1, -1) * 1e-6
    g_in = np.vstack([g_ss * (1 + 0.08 * idx) for idx in range(6)])
    c_nsc_ss = np.linspace(130.0, 220.0, n_points).reshape(1, -1) + 5 * offset

    savemat(
        directory / filename,
        {
            "PARAM": np.array([param], dtype=object),
            "PARAM_TEST": param_test,
            "VPD_ss_test": vpd_ss,
            "VPD_test": vpd_in,
            "eta_test": np.array([[0.216, 0.288, 0.360, 0.432, 0.504, 0.576]]),
            "gamma_r_test": np.array([[0.38]]),
            "study_legend": _study_legend_array(),
            "study_VPD": vpd_study,
            "g_c_ss_test": g_c_ss,
            "g_c_test": g_c_in,
            "study_g_c": g_c_study,
            "lambda_ss_test": lambda_ss,
            "lambda_test": lambda_in,
            "study_lambda": lambda_study,
            "G_ss_test": g_ss,
            "G_test": g_in,
            "c_NSC_ss_test": c_nsc_ss,
            "E_ss_test": g_ss,
            "E_test": g_in,
            "study_E": np.vstack([g_ss * (1 + 0.03 * idx) for idx in range(7)]),
        },
    )


def _build_legacy_dir(tmp_path: Path) -> Path:
    legacy_dir = tmp_path / "legacy"
    _write_sensitivity_mat(
        legacy_dir,
        filename="Growth_Opt_Stomata__test_sensitivity__RH.mat",
        param="RH",
        n_points=7,
        offset=0.00,
    )
    _write_sensitivity_mat(
        legacy_dir,
        filename="Growth_Opt_Stomata__test_sensitivity__c_a.mat",
        param="c_a",
        n_points=6,
        offset=0.01,
    )
    _write_sensitivity_mat(
        legacy_dir,
        filename="Growth_Opt_Stomata__test_sensitivity__P_soil.mat",
        param="P_soil",
        n_points=5,
        offset=0.02,
    )
    _write_sensitivity_mat(
        legacy_dir,
        filename="Growth_Opt_Stomata__test_sensitivity__P_soil_min__true_k_loss.mat",
        param="P_soil_min",
        n_points=5,
        offset=0.00,
    )
    _write_sensitivity_mat(
        legacy_dir,
        filename="Growth_Opt_Stomata__test_sensitivity__P_soil_min__imag_k_loss.mat",
        param="P_soil_min",
        n_points=8,
        offset=0.03,
    )
    return legacy_dir


def test_load_sensitivity_scenario_parses_axes(tmp_path: Path) -> None:
    legacy_dir = _build_legacy_dir(tmp_path)
    scenario = load_sensitivity_scenario(legacy_dir / "Growth_Opt_Stomata__test_sensitivity__c_a.mat")

    assert scenario.param == "c_a"
    assert scenario.column_title == "Atmospheric CO2"
    assert scenario.instantaneous["c_nsc"].shape == scenario.instantaneous["g_c"].shape
    assert float(scenario.instantaneous["c_nsc"][0, 0]) == 175.0


def test_build_sensitivity_frames_from_fixture_dir(tmp_path: Path) -> None:
    legacy_dir = _build_legacy_dir(tmp_path)

    compare_frame = build_compare_true_vs_imag_frame(legacy_example_dir=legacy_dir)
    all_frame = build_sensitivity_all_frame(legacy_example_dir=legacy_dir)
    some_frame = build_sensitivity_some_frame(legacy_example_dir=legacy_dir)

    assert {"scenario_id", "response_kind", "metric", "x", "y"} <= set(compare_frame.columns)
    assert set(all_frame["scenario_id"]) == {"RH", "c_a", "P_soil", "P_soil_min"}
    assert set(some_frame["response_kind"]) == {"steady_state", "study_all"}


def test_render_sensitivity_suite_writes_expected_artifacts(tmp_path: Path) -> None:
    legacy_dir = _build_legacy_dir(tmp_path)
    artifacts = render_sensitivity_figure_suite(
        legacy_example_dir=legacy_dir,
        output_dir=tmp_path / "out",
    )

    assert artifacts.compare_true_vs_imag.png_path.exists()
    assert artifacts.sensitivity_all.pdf_path.exists()
    assert artifacts.sensitivity_some.metadata_path.exists()
    compare_metadata = json.loads(artifacts.compare_true_vs_imag.metadata_path.read_text(encoding="utf-8"))
    assert compare_metadata["legacy_digest_summary"]["actual"]


def test_render_gosm_sensitivity_figures_script_entrypoint(tmp_path: Path) -> None:
    legacy_dir = _build_legacy_dir(tmp_path)
    result = subprocess.run(
        [
            sys.executable,
            str(_script_path()),
            "--legacy-example-dir",
            str(legacy_dir),
            "--output-dir",
            str(tmp_path / "rendered"),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    summary = json.loads(result.stdout)

    assert Path(summary["compare_true_vs_imag"]["png"]).exists()
    assert Path(summary["sensitivity_all"]["pdf"]).exists()
    assert Path(summary["sensitivity_some"]["metadata"]).exists()


def test_build_parser_defaults_to_workspace_paths() -> None:
    module = _load_script_module()
    parser = module.build_parser()
    args = parser.parse_args([])

    assert args.output_dir.name == "sensitivity_figures"
    assert args.compare_spec.name == "compare_true_vs_imag_figure.yaml"
