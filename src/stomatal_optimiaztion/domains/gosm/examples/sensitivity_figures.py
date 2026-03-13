from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from typing import Any
import json

import numpy as np
import pandas as pd
from scipy.io import loadmat

from stomatal_optimiaztion.domains.gosm.examples._plotkit import (
    FigureBundleArtifacts,
    apply_axis_theme,
    frame_digest,
    load_yaml,
    resolve_figure_paths,
)
from stomatal_optimiaztion.domains.gosm.params import BaselineInputs

REPO_ROOT = Path(__file__).resolve().parents[5]
WORKSPACE_ROOT = REPO_ROOT.parents[1]

DEFAULT_LEGACY_GOSM_EXAMPLE_DIR = WORKSPACE_ROOT / "00. Stomatal Optimization" / "GOSM" / "example"
DEFAULT_SENSITIVITY_OUTPUT_DIR = REPO_ROOT / "out" / "gosm" / "sensitivity_figures"
DEFAULT_COMPARE_TRUE_IMAG_SPEC_PATH = REPO_ROOT / "configs" / "plotkit" / "gosm" / "compare_true_vs_imag_figure.yaml"
DEFAULT_SENSITIVITY_ALL_SPEC_PATH = REPO_ROOT / "configs" / "plotkit" / "gosm" / "sensitivity_all_figure.yaml"
DEFAULT_SENSITIVITY_SOME_SPEC_PATH = REPO_ROOT / "configs" / "plotkit" / "gosm" / "sensitivity_some_figure.yaml"

DEFAULT_INSTANTANEOUS_NSC_MOL = 175.0
ETA_NORMALIZER = 1.0 - BaselineInputs.matlab_default().f_c

TRUE_VS_IMAG_FILENAMES = {
    "true": "Growth_Opt_Stomata__test_sensitivity__P_soil_min__true_k_loss.mat",
    "imag": "Growth_Opt_Stomata__test_sensitivity__P_soil_min__imag_k_loss.mat",
}

SENSITIVITY_FILENAMES = {
    "RH": "Growth_Opt_Stomata__test_sensitivity__RH.mat",
    "c_a": "Growth_Opt_Stomata__test_sensitivity__c_a.mat",
    "P_soil": "Growth_Opt_Stomata__test_sensitivity__P_soil.mat",
    "P_soil_min": "Growth_Opt_Stomata__test_sensitivity__P_soil_min__true_k_loss.mat",
}

EXPECTED_FRAME_DIGESTS: dict[str, str | None] = {
    "compare_true_vs_imag": "2cd99cde31987687d5b1178e83d1a7554a825be1e416cd083dafd2cec4363195",
    "sensitivity_all": "e935ff35b27a4bb28157e976dc6f4c2145a1195f71b8b0f10d6a779454f5075f",
    "sensitivity_some": "4ea5026987d6fa5b0dc32857fdec057335a213481b277ba57ef6abe9fdf1c647",
}

PARAM_METADATA = {
    "RH": {
        "column_title": "VPD",
        "x_label": "Vapor pressure deficit (VPD), D_L [kPa]",
        "multiplier": 1.0,
    },
    "c_a": {
        "column_title": "Atmospheric CO2",
        "x_label": "Atmospheric CO2 pressure, c_a [Pa]",
        "multiplier": 101.325 * 1e3,
    },
    "P_soil": {
        "column_title": "Soil water potential",
        "x_label": "Soil water potential, -psi_soil [MPa]",
        "multiplier": -1.0,
    },
    "P_soil_min": {
        "column_title": "Minimum soil water potential",
        "x_label": "Minimum experienced soil water potential, -psi_soil^min [MPa]",
        "multiplier": -1.0,
    },
}

METRIC_FRAME_KEYS = {
    "g_c": "g_c_mol_m2_s",
    "lambda": "lambda_wue_mol_mol",
    "growth": "growth_umol_c_s",
    "c_nsc": "c_nsc_mol",
}

SELECTED_STUDY_INDICES = (0, 2, 3)
STUDY_STYLE_MAP = {
    "Cowan & Farquhar (1977)": {"color": "#F95738", "linestyle": "-.", "label": "Cowan & Farquhar (1977)"},
    "Prentice et al. (2014)": {"color": "#EE964B", "linestyle": "-", "label": "Prentice et al. (2014)"},
    "Sperry et al. (2017)": {"color": "#3A86FF", "linestyle": ":", "label": "Sperry et al. (2017)"},
    "Anderegg et al. (2018)": {
        "color": "#6A4C93",
        "linestyle": "-.",
        "label": "Wolf et al. (2016) & Anderegg et al. (2018)",
    },
    "Dewar et al. (2018)": {"color": "#3FA34D", "linestyle": "-", "label": "Dewar et al. (2018)"},
    "Eller et al. (2018)": {"color": "#0A9396", "linestyle": ":", "label": "Eller et al. (2018)"},
    "Wang et al. (2020)": {"color": "#264653", "linestyle": "--", "label": "Wang et al. (2020)"},
}


@dataclass(frozen=True)
class SensitivityScenario:
    scenario_id: str
    source_mat_path: Path
    param: str
    column_title: str
    x_label: str
    x_ss_mat: np.ndarray
    x_in_mat: np.ndarray
    x_study_mat: np.ndarray
    x_limits: tuple[float, float]
    eta_test: np.ndarray
    gamma_r_test: np.ndarray
    study_legend: tuple[str, ...]
    steady_state: dict[str, np.ndarray]
    instantaneous: dict[str, np.ndarray]
    study: dict[str, np.ndarray]


@dataclass(frozen=True)
class GOSMSensitivityFigureSuiteArtifacts:
    compare_true_vs_imag: FigureBundleArtifacts
    sensitivity_all: FigureBundleArtifacts
    sensitivity_some: FigureBundleArtifacts

    def to_summary(self) -> dict[str, Any]:
        return {
            "compare_true_vs_imag": self.compare_true_vs_imag.to_summary(),
            "sensitivity_all": self.sensitivity_all.to_summary(),
            "sensitivity_some": self.sensitivity_some.to_summary(),
        }


def _matlab_string(value: Any) -> str:
    if isinstance(value, str):
        return value
    array = np.asarray(value)
    if array.dtype == object:
        return _matlab_string(array.flat[0])
    flattened = array.reshape(-1)
    if flattened.size == 0:
        return ""
    return str(flattened[0])


def _as_2d_float(value: Any) -> np.ndarray:
    array = np.asarray(value, dtype=float)
    if array.ndim == 1:
        return array.reshape(1, -1)
    return array


def _as_1d_float(value: Any) -> np.ndarray:
    return np.asarray(value, dtype=float).reshape(-1)


def _repeat_rows(base: np.ndarray, rows: int) -> np.ndarray:
    return np.repeat(_as_2d_float(base), rows, axis=0)


def _scenario_style(spec: dict[str, Any], scenario_id: str) -> dict[str, Any]:
    styles = spec["styling"]["scenarios"]
    if scenario_id not in styles:
        raise KeyError(f"Missing scenario style for '{scenario_id}'")
    return styles[scenario_id]


def _study_style(label: str) -> dict[str, str]:
    if label not in STUDY_STYLE_MAP:
        raise KeyError(f"Missing study style for '{label}'")
    return STUDY_STYLE_MAP[label]


def _panel_label(ax: Any, *, tokens: dict[str, Any], letter: str) -> None:
    panel_tokens = tokens["panel_labels"]
    fonts = tokens["fonts"]
    ax.text(
        panel_tokens["x"],
        panel_tokens["y"],
        f"{panel_tokens['prefix']}{letter}{panel_tokens['suffix']}",
        transform=ax.transAxes,
        ha=panel_tokens["ha"],
        va=panel_tokens["va"],
        fontsize=fonts["panel_label_size_pt"],
        fontweight=fonts["weight_labels"],
    )


def _tokens_path_from_spec(spec_path: Path, spec: dict[str, Any]) -> Path:
    return (spec_path.parent / spec["theme"]["tokens"]).resolve()


def _legacy_digest_summary(frame: pd.DataFrame, *, digest_key: str) -> dict[str, Any]:
    actual = frame_digest(frame)
    expected = EXPECTED_FRAME_DIGESTS[digest_key]
    return {
        "digest_key": digest_key,
        "expected": expected,
        "actual": actual,
        "passed": None if expected is None else expected == actual,
    }


def load_sensitivity_scenario(mat_path: Path, *, scenario_id: str | None = None) -> SensitivityScenario:
    mat_path = mat_path.resolve()
    mat = loadmat(mat_path)

    param = _matlab_string(mat["PARAM"])
    if param not in PARAM_METADATA:
        raise ValueError(f"Unsupported sensitivity parameter '{param}' in {mat_path}")
    metadata = PARAM_METADATA[param]
    scenario_id = scenario_id or param

    eta_test = _as_1d_float(mat["eta_test"])
    gamma_r_test = _as_1d_float(mat["gamma_r_test"])
    study_legend = tuple(_matlab_string(item) for item in np.asarray(mat["study_legend"], dtype=object).reshape(-1))

    param_test = _as_2d_float(mat["PARAM_TEST"])
    multiplier = float(metadata["multiplier"])
    if param == "RH":
        x_ss_mat = multiplier * _as_2d_float(mat["VPD_ss_test"])
        x_in_mat = multiplier * _as_2d_float(mat["VPD_test"])
        x_study_mat = multiplier * _as_2d_float(mat["study_VPD"])
    else:
        x_ss_mat = multiplier * _repeat_rows(param_test, rows=len(gamma_r_test))
        x_in_mat = multiplier * _repeat_rows(param_test, rows=len(eta_test))
        x_study_mat = multiplier * _repeat_rows(param_test, rows=len(study_legend))

    xmin = float(min(np.nanmin(x_ss_mat), np.nanmin(x_in_mat), np.nanmin(x_study_mat)))
    xmax = float(max(np.nanmax(x_ss_mat), np.nanmax(x_in_mat), np.nanmax(x_study_mat)))
    if param == "P_soil":
        xmax = min(0.8, xmax)

    g_c_in = _as_2d_float(mat["g_c_test"])
    instantaneous_nsc = np.full_like(g_c_in, DEFAULT_INSTANTANEOUS_NSC_MOL)

    return SensitivityScenario(
        scenario_id=scenario_id,
        source_mat_path=mat_path,
        param=param,
        column_title=str(metadata["column_title"]),
        x_label=str(metadata["x_label"]),
        x_ss_mat=x_ss_mat,
        x_in_mat=x_in_mat,
        x_study_mat=x_study_mat,
        x_limits=(xmin, xmax),
        eta_test=eta_test,
        gamma_r_test=gamma_r_test,
        study_legend=study_legend,
        steady_state={
            "g_c": _as_2d_float(mat["g_c_ss_test"]),
            "lambda": _as_2d_float(mat["lambda_ss_test"]),
            "growth": 1e6 * _as_2d_float(mat["G_ss_test"]),
            "c_nsc": _as_2d_float(mat["c_NSC_ss_test"]),
        },
        instantaneous={
            "g_c": g_c_in,
            "lambda": _as_2d_float(mat["lambda_test"]),
            "growth": 1e6 * _as_2d_float(mat["G_test"]),
            "c_nsc": instantaneous_nsc,
        },
        study={
            "g_c": _as_2d_float(mat["study_g_c"]),
            "lambda": _as_2d_float(mat["study_lambda"]),
        },
    )


def _iter_metric_rows(
    scenario: SensitivityScenario,
    *,
    metric_key: str,
    response_kind: str,
    metric_frame_key: str,
) -> list[dict[str, Any]]:
    if response_kind == "steady_state":
        x_matrix = scenario.x_ss_mat
        y_matrix = scenario.steady_state[metric_key]
        line_values = scenario.gamma_r_test
        label_prefix = "gamma_r="
    elif response_kind == "instantaneous":
        x_matrix = scenario.x_in_mat
        y_matrix = scenario.instantaneous[metric_key]
        line_values = scenario.eta_test / ETA_NORMALIZER
        label_prefix = "eta_factor="
    else:
        x_matrix = scenario.x_study_mat
        y_matrix = scenario.study[metric_key]
        line_values = list(scenario.study_legend)
        label_prefix = "study="

    records: list[dict[str, Any]] = []
    for line_idx in range(y_matrix.shape[0]):
        label_value = line_values[line_idx]
        for x, y in zip(x_matrix[line_idx], y_matrix[line_idx], strict=True):
            records.append(
                {
                    "scenario_id": scenario.scenario_id,
                    "param": scenario.param,
                    "response_kind": response_kind,
                    "line_index": line_idx,
                    "line_label": f"{label_prefix}{label_value}",
                    "metric": metric_frame_key,
                    "x": float(x),
                    "y": float(y),
                }
            )
    return records


def build_compare_true_vs_imag_frame(*, legacy_example_dir: Path) -> pd.DataFrame:
    scenarios = (
        load_sensitivity_scenario(legacy_example_dir / TRUE_VS_IMAG_FILENAMES["true"], scenario_id="true"),
        load_sensitivity_scenario(legacy_example_dir / TRUE_VS_IMAG_FILENAMES["imag"], scenario_id="imag"),
    )
    records: list[dict[str, Any]] = []
    for scenario in scenarios:
        for metric_key, frame_key in METRIC_FRAME_KEYS.items():
            records.extend(
                _iter_metric_rows(
                    scenario,
                    metric_key=metric_key,
                    response_kind="steady_state",
                    metric_frame_key=frame_key,
                )
            )
            records.extend(
                _iter_metric_rows(
                    scenario,
                    metric_key=metric_key,
                    response_kind="instantaneous",
                    metric_frame_key=frame_key,
                )
            )
    return pd.DataFrame.from_records(records)


def build_sensitivity_all_frame(*, legacy_example_dir: Path) -> pd.DataFrame:
    records: list[dict[str, Any]] = []
    for param, filename in SENSITIVITY_FILENAMES.items():
        scenario = load_sensitivity_scenario(legacy_example_dir / filename, scenario_id=param)
        for metric_key, frame_key in METRIC_FRAME_KEYS.items():
            records.extend(
                _iter_metric_rows(
                    scenario,
                    metric_key=metric_key,
                    response_kind="steady_state",
                    metric_frame_key=frame_key,
                )
            )
            records.extend(
                _iter_metric_rows(
                    scenario,
                    metric_key=metric_key,
                    response_kind="instantaneous",
                    metric_frame_key=frame_key,
                )
            )
        for metric_key in ("g_c", "lambda"):
            frame_key = METRIC_FRAME_KEYS[metric_key]
            for study_idx in SELECTED_STUDY_INDICES:
                study_label = scenario.study_legend[study_idx]
                for x, y in zip(
                    scenario.x_study_mat[study_idx],
                    scenario.study[metric_key][study_idx],
                    strict=True,
                ):
                    records.append(
                        {
                            "scenario_id": scenario.scenario_id,
                            "param": scenario.param,
                            "response_kind": "study_selected",
                            "line_index": study_idx,
                            "line_label": study_label,
                            "metric": frame_key,
                            "x": float(x),
                            "y": float(y),
                        }
                    )
    return pd.DataFrame.from_records(records)


def build_sensitivity_some_frame(*, legacy_example_dir: Path) -> pd.DataFrame:
    records: list[dict[str, Any]] = []
    for param, filename in SENSITIVITY_FILENAMES.items():
        scenario = load_sensitivity_scenario(legacy_example_dir / filename, scenario_id=param)
        for metric_key in ("g_c", "lambda"):
            frame_key = METRIC_FRAME_KEYS[metric_key]
            records.extend(
                _iter_metric_rows(
                    scenario,
                    metric_key=metric_key,
                    response_kind="steady_state",
                    metric_frame_key=frame_key,
                )
            )
            for study_idx, study_label in enumerate(scenario.study_legend):
                for x, y in zip(
                    scenario.x_study_mat[study_idx],
                    scenario.study[metric_key][study_idx],
                    strict=True,
                ):
                    records.append(
                        {
                            "scenario_id": scenario.scenario_id,
                            "param": scenario.param,
                            "response_kind": "study_all",
                            "line_index": study_idx,
                            "line_label": study_label,
                            "metric": frame_key,
                            "x": float(x),
                            "y": float(y),
                        }
                    )
    return pd.DataFrame.from_records(records)


def _common_bundle_prep(
    *,
    output_dir: Path,
    spec_path: Path,
    figure_id: str,
    resolved_spec: dict[str, Any],
    frame: pd.DataFrame,
) -> tuple[dict[str, Any], dict[str, Path], dict[str, Any]]:
    spec = load_yaml(spec_path)
    tokens_path = _tokens_path_from_spec(spec_path, spec)
    tokens = load_yaml(tokens_path)
    file_paths = resolve_figure_paths(output_dir, figure_id)

    frame.to_csv(file_paths["data_csv"], index=False)
    file_paths["spec_copy"].write_text(spec_path.read_text(encoding="utf-8"), encoding="utf-8")
    file_paths["resolved_spec"].write_text(json.dumps(resolved_spec, indent=2), encoding="utf-8")
    file_paths["tokens_copy"].write_text(tokens_path.read_text(encoding="utf-8"), encoding="utf-8")
    return spec, file_paths, tokens


def render_compare_true_vs_imag_bundle(
    *,
    legacy_example_dir: Path | None = None,
    output_dir: Path | None = None,
    spec_path: Path | None = None,
) -> FigureBundleArtifacts:
    import matplotlib.pyplot as plt

    legacy_example_dir = (legacy_example_dir or DEFAULT_LEGACY_GOSM_EXAMPLE_DIR).resolve()
    output_dir = (output_dir or DEFAULT_SENSITIVITY_OUTPUT_DIR / "compare_true_vs_imag").resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    spec_path = (spec_path or DEFAULT_COMPARE_TRUE_IMAG_SPEC_PATH).resolve()

    true_scenario = load_sensitivity_scenario(legacy_example_dir / TRUE_VS_IMAG_FILENAMES["true"], scenario_id="true")
    imag_scenario = load_sensitivity_scenario(legacy_example_dir / TRUE_VS_IMAG_FILENAMES["imag"], scenario_id="imag")
    frame = build_compare_true_vs_imag_frame(legacy_example_dir=legacy_example_dir)
    digest_summary = _legacy_digest_summary(frame, digest_key="compare_true_vs_imag")

    spec = load_yaml(spec_path)
    figure_id = spec["meta"]["id"]
    resolved_spec = deepcopy(spec)
    resolved_spec["data"] = {
        "path": str((output_dir / f"{figure_id}_data.csv").resolve()),
        "row_count": int(len(frame)),
        "columns": list(frame.columns),
    }
    resolved_spec["meta"]["legacy_digest_match"] = digest_summary["passed"]
    resolved_spec["meta"]["source_mats"] = [str(true_scenario.source_mat_path), str(imag_scenario.source_mat_path)]

    spec, file_paths, tokens = _common_bundle_prep(
        output_dir=output_dir,
        spec_path=spec_path,
        figure_id=figure_id,
        resolved_spec=resolved_spec,
        frame=frame,
    )

    width_mm = float(spec["figure"]["width_mm"])
    height_mm = float(spec["figure"]["height_mm"])
    dpi = int(spec["export"]["dpi"])
    fig, axes = plt.subplots(
        2,
        2,
        figsize=(width_mm / 25.4, height_mm / 25.4),
        dpi=dpi,
        facecolor=tokens["figure"]["background"],
        constrained_layout=False,
    )
    fig.subplots_adjust(left=0.12, right=0.73, bottom=0.12, top=0.92, wspace=0.25, hspace=0.28)

    scenarios = (true_scenario, imag_scenario)
    shared_limits = (
        min(true_scenario.x_limits[0], imag_scenario.x_limits[0]),
        max(true_scenario.x_limits[1], imag_scenario.x_limits[1]),
    )
    fonts = tokens["fonts"]
    panel_letters = iter("abcd")
    steady_handles: list[Any] = []
    instant_handles: list[Any] = []
    steady_labels: list[str] = []
    instant_labels: list[str] = []

    for panel_spec, ax in zip(spec["panels"], axes.reshape(-1), strict=True):
        metric_key = panel_spec["metric_key"]
        show_xlabels = bool(panel_spec["show_xlabels"])
        apply_axis_theme(ax, tokens=tokens, show_xlabels=show_xlabels)
        ax.set_xlim(shared_limits)
        ax.set_ylim(panel_spec["limits"])
        ax.set_yscale(panel_spec["scale"])
        ax.set_ylabel(panel_spec["y_label"], fontsize=fonts["axis_label_size_pt"])
        if show_xlabels:
            ax.set_xlabel(spec["x_axis"]["label"], fontsize=fonts["axis_label_size_pt"])

        for scenario in scenarios:
            style = _scenario_style(spec, scenario.scenario_id)
            steady_matrix = scenario.steady_state[metric_key]
            for line_idx in range(steady_matrix.shape[0]):
                line = ax.plot(
                    scenario.x_ss_mat[line_idx],
                    steady_matrix[line_idx],
                    color=style["steady_color"],
                    linestyle=style["steady_linestyle"],
                    linewidth=style["steady_linewidth_pt"],
                    alpha=1.0,
                )[0]
                if metric_key == "g_c" and line_idx == 0:
                    steady_handles.append(line)
                    steady_labels.append(style["steady_label"])

            instant_matrix = scenario.instantaneous[metric_key]
            cmap = plt.get_cmap(style["instant_cmap"])
            colors = cmap(np.linspace(0.45, 0.9, instant_matrix.shape[0]))
            for line_idx in range(instant_matrix.shape[0]):
                line = ax.plot(
                    scenario.x_in_mat[line_idx],
                    instant_matrix[line_idx],
                    color=colors[line_idx],
                    linestyle=style["instant_linestyle"],
                    linewidth=style["instant_linewidth_pt"],
                    alpha=style["instant_alpha"],
                )[0]
                if metric_key == "g_c":
                    instant_handles.append(line)
                    instant_labels.append(f"{style['instant_label_prefix']}; eta={scenario.eta_test[line_idx] / ETA_NORMALIZER:.3f}")

        _panel_label(ax, tokens=tokens, letter=next(panel_letters))
        ax.set_title(panel_spec["title"], fontsize=fonts["title_size_pt"], loc="left", pad=6)

    fig.legend(
        steady_handles,
        steady_labels,
        loc="upper right",
        bbox_to_anchor=(0.99, 0.96),
        frameon=tokens["legend"]["frameon"],
        fontsize=fonts["legend_size_pt"],
    )
    fig.legend(
        instant_handles,
        instant_labels,
        loc="lower right",
        bbox_to_anchor=(0.995, 0.06),
        frameon=tokens["legend"]["frameon"],
        fontsize=fonts["legend_size_pt"] - 0.2,
    )

    fig.savefig(file_paths["png"], dpi=dpi, transparent=spec["export"]["transparent"], facecolor=tokens["figure"]["background"])
    fig.savefig(file_paths["pdf"], dpi=dpi, transparent=spec["export"]["transparent"], facecolor=tokens["figure"]["background"])
    plt.close(fig)

    metadata = {
        "figure_id": figure_id,
        "source_mats": [str(true_scenario.source_mat_path), str(imag_scenario.source_mat_path)],
        "legacy_digest_summary": digest_summary,
        "outputs": {key: str(value) for key, value in file_paths.items()},
    }
    file_paths["metadata"].write_text(json.dumps(metadata, indent=2), encoding="utf-8")

    return FigureBundleArtifacts(
        output_dir=output_dir,
        data_csv_path=file_paths["data_csv"],
        spec_copy_path=file_paths["spec_copy"],
        resolved_spec_path=file_paths["resolved_spec"],
        tokens_copy_path=file_paths["tokens_copy"],
        metadata_path=file_paths["metadata"],
        png_path=file_paths["png"],
        pdf_path=file_paths["pdf"],
    )


def render_sensitivity_all_bundle(
    *,
    legacy_example_dir: Path | None = None,
    output_dir: Path | None = None,
    spec_path: Path | None = None,
) -> FigureBundleArtifacts:
    import matplotlib.pyplot as plt

    legacy_example_dir = (legacy_example_dir or DEFAULT_LEGACY_GOSM_EXAMPLE_DIR).resolve()
    output_dir = (output_dir or DEFAULT_SENSITIVITY_OUTPUT_DIR / "sensitivity_all").resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    spec_path = (spec_path or DEFAULT_SENSITIVITY_ALL_SPEC_PATH).resolve()

    scenarios = [load_sensitivity_scenario(legacy_example_dir / filename, scenario_id=param) for param, filename in SENSITIVITY_FILENAMES.items()]
    frame = build_sensitivity_all_frame(legacy_example_dir=legacy_example_dir)
    digest_summary = _legacy_digest_summary(frame, digest_key="sensitivity_all")

    spec = load_yaml(spec_path)
    figure_id = spec["meta"]["id"]
    resolved_spec = deepcopy(spec)
    resolved_spec["data"] = {
        "path": str((output_dir / f"{figure_id}_data.csv").resolve()),
        "row_count": int(len(frame)),
        "columns": list(frame.columns),
    }
    resolved_spec["meta"]["legacy_digest_match"] = digest_summary["passed"]
    resolved_spec["meta"]["source_mats"] = [str(scenario.source_mat_path) for scenario in scenarios]

    spec, file_paths, tokens = _common_bundle_prep(
        output_dir=output_dir,
        spec_path=spec_path,
        figure_id=figure_id,
        resolved_spec=resolved_spec,
        frame=frame,
    )

    width_mm = float(spec["figure"]["width_mm"])
    height_mm = float(spec["figure"]["height_mm"])
    dpi = int(spec["export"]["dpi"])
    fig, axes = plt.subplots(
        len(spec["rows"]),
        len(scenarios),
        figsize=(width_mm / 25.4, height_mm / 25.4),
        dpi=dpi,
        facecolor=tokens["figure"]["background"],
        constrained_layout=False,
    )
    fig.subplots_adjust(left=0.10, right=0.80, bottom=0.12, top=0.91, wspace=0.18, hspace=0.24)
    fonts = tokens["fonts"]

    representative_handles: dict[str, Any] = {}
    panel_index = 0
    for row_idx, row_spec in enumerate(spec["rows"]):
        metric_key = row_spec["metric_key"]
        for col_idx, scenario in enumerate(scenarios):
            ax = axes[row_idx, col_idx]
            show_xlabels = row_idx == len(spec["rows"]) - 1
            apply_axis_theme(ax, tokens=tokens, show_xlabels=show_xlabels)
            ax.set_xlim(scenario.x_limits)
            ax.set_ylim(row_spec["limits"])
            ax.set_yscale(row_spec["scale"])
            if col_idx == 0:
                ax.set_ylabel(row_spec["y_label"], fontsize=fonts["axis_label_size_pt"])
            else:
                ax.tick_params(labelleft=False)
            if show_xlabels:
                ax.set_xlabel(scenario.x_label, fontsize=fonts["axis_label_size_pt"])
            if row_idx == 0:
                ax.set_title(scenario.column_title, fontsize=fonts["title_size_pt"], pad=8)

            study_matrix = scenario.study.get(metric_key)
            if study_matrix is not None and row_spec.get("include_selected_studies", False):
                for study_idx in SELECTED_STUDY_INDICES:
                    label = scenario.study_legend[study_idx]
                    style = _study_style(label)
                    line = ax.plot(
                        scenario.x_study_mat[study_idx],
                        study_matrix[study_idx],
                        color=style["color"],
                        linestyle=style["linestyle"],
                        linewidth=float(spec["styling"]["study_linewidth_pt"]),
                    )[0]
                    representative_handles.setdefault(style["label"], line)

            instant_matrix = scenario.instantaneous[metric_key]
            colors = plt.get_cmap(spec["styling"]["instantaneous_cmap"])(np.linspace(0.35, 0.85, instant_matrix.shape[0]))
            for line_idx in range(instant_matrix.shape[0]):
                line = ax.plot(
                    scenario.x_in_mat[line_idx],
                    instant_matrix[line_idx],
                    color=colors[line_idx],
                    linestyle=spec["styling"]["instantaneous_linestyle"],
                    linewidth=float(spec["styling"]["instantaneous_linewidth_pt"]),
                    alpha=float(spec["styling"]["instantaneous_alpha"]),
                )[0]
                representative_handles.setdefault("Instantaneous GOH", line)

            steady_matrix = scenario.steady_state[metric_key]
            for line_idx in range(steady_matrix.shape[0]):
                line = ax.plot(
                    scenario.x_ss_mat[line_idx],
                    steady_matrix[line_idx],
                    color=spec["styling"]["steady_state_color"],
                    linestyle=spec["styling"]["steady_state_linestyle"],
                    linewidth=float(spec["styling"]["steady_state_linewidth_pt"]),
                )[0]
                representative_handles.setdefault("Steady-state GOH", line)

            _panel_label(ax, tokens=tokens, letter=chr(97 + panel_index))
            panel_index += 1

    legend_order = [
        "Steady-state GOH",
        "Instantaneous GOH",
        _study_style("Cowan & Farquhar (1977)")["label"],
        _study_style("Sperry et al. (2017)")["label"],
        _study_style("Anderegg et al. (2018)")["label"],
    ]
    fig.legend(
        [representative_handles[label] for label in legend_order],
        legend_order,
        loc="center right",
        bbox_to_anchor=(0.99, 0.5),
        frameon=tokens["legend"]["frameon"],
        fontsize=fonts["legend_size_pt"],
    )
    fig.text(0.44, 0.965, spec["meta"]["title"], ha="center", va="center", fontsize=fonts["title_size_pt"] + 2, fontweight="bold")

    fig.savefig(file_paths["png"], dpi=dpi, transparent=spec["export"]["transparent"], facecolor=tokens["figure"]["background"])
    fig.savefig(file_paths["pdf"], dpi=dpi, transparent=spec["export"]["transparent"], facecolor=tokens["figure"]["background"])
    plt.close(fig)

    metadata = {
        "figure_id": figure_id,
        "source_mats": [str(scenario.source_mat_path) for scenario in scenarios],
        "legacy_digest_summary": digest_summary,
        "outputs": {key: str(value) for key, value in file_paths.items()},
    }
    file_paths["metadata"].write_text(json.dumps(metadata, indent=2), encoding="utf-8")

    return FigureBundleArtifacts(
        output_dir=output_dir,
        data_csv_path=file_paths["data_csv"],
        spec_copy_path=file_paths["spec_copy"],
        resolved_spec_path=file_paths["resolved_spec"],
        tokens_copy_path=file_paths["tokens_copy"],
        metadata_path=file_paths["metadata"],
        png_path=file_paths["png"],
        pdf_path=file_paths["pdf"],
    )


def render_sensitivity_some_bundle(
    *,
    legacy_example_dir: Path | None = None,
    output_dir: Path | None = None,
    spec_path: Path | None = None,
) -> FigureBundleArtifacts:
    import matplotlib.pyplot as plt

    legacy_example_dir = (legacy_example_dir or DEFAULT_LEGACY_GOSM_EXAMPLE_DIR).resolve()
    output_dir = (output_dir or DEFAULT_SENSITIVITY_OUTPUT_DIR / "sensitivity_some").resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    spec_path = (spec_path or DEFAULT_SENSITIVITY_SOME_SPEC_PATH).resolve()

    scenarios = [load_sensitivity_scenario(legacy_example_dir / filename, scenario_id=param) for param, filename in SENSITIVITY_FILENAMES.items()]
    frame = build_sensitivity_some_frame(legacy_example_dir=legacy_example_dir)
    digest_summary = _legacy_digest_summary(frame, digest_key="sensitivity_some")

    spec = load_yaml(spec_path)
    figure_id = spec["meta"]["id"]
    resolved_spec = deepcopy(spec)
    resolved_spec["data"] = {
        "path": str((output_dir / f"{figure_id}_data.csv").resolve()),
        "row_count": int(len(frame)),
        "columns": list(frame.columns),
    }
    resolved_spec["meta"]["legacy_digest_match"] = digest_summary["passed"]
    resolved_spec["meta"]["source_mats"] = [str(scenario.source_mat_path) for scenario in scenarios]

    spec, file_paths, tokens = _common_bundle_prep(
        output_dir=output_dir,
        spec_path=spec_path,
        figure_id=figure_id,
        resolved_spec=resolved_spec,
        frame=frame,
    )

    width_mm = float(spec["figure"]["width_mm"])
    height_mm = float(spec["figure"]["height_mm"])
    dpi = int(spec["export"]["dpi"])
    fig, axes = plt.subplots(
        len(spec["rows"]),
        len(scenarios),
        figsize=(width_mm / 25.4, height_mm / 25.4),
        dpi=dpi,
        facecolor=tokens["figure"]["background"],
        constrained_layout=False,
    )
    fig.subplots_adjust(left=0.10, right=0.78, bottom=0.16, top=0.89, wspace=0.18, hspace=0.28)
    fonts = tokens["fonts"]

    representative_handles: dict[str, Any] = {}
    panel_index = 0
    for row_idx, row_spec in enumerate(spec["rows"]):
        metric_key = row_spec["metric_key"]
        for col_idx, scenario in enumerate(scenarios):
            ax = axes[row_idx, col_idx]
            show_xlabels = row_idx == len(spec["rows"]) - 1
            apply_axis_theme(ax, tokens=tokens, show_xlabels=show_xlabels)
            ax.set_xlim(scenario.x_limits)
            ax.set_ylim(row_spec["limits"])
            ax.set_yscale(row_spec["scale"])
            if col_idx == 0:
                ax.set_ylabel(row_spec["y_label"], fontsize=fonts["axis_label_size_pt"])
            else:
                ax.tick_params(labelleft=False)
            if show_xlabels:
                ax.set_xlabel(scenario.x_label, fontsize=fonts["axis_label_size_pt"])
            if row_idx == 0:
                ax.set_title(scenario.column_title, fontsize=fonts["title_size_pt"], pad=8)

            steady_matrix = scenario.steady_state[metric_key]
            for line_idx in range(steady_matrix.shape[0]):
                line = ax.plot(
                    scenario.x_ss_mat[line_idx],
                    steady_matrix[line_idx],
                    color=spec["styling"]["steady_state_color"],
                    linestyle=spec["styling"]["steady_state_linestyle"],
                    linewidth=float(spec["styling"]["steady_state_linewidth_pt"]),
                )[0]
                representative_handles.setdefault("Steady-state GOH", line)

            for study_idx, study_label in enumerate(scenario.study_legend):
                style = _study_style(study_label)
                line = ax.plot(
                    scenario.x_study_mat[study_idx],
                    scenario.study[metric_key][study_idx],
                    color=style["color"],
                    linestyle=style["linestyle"],
                    linewidth=float(spec["styling"]["study_linewidth_pt"]),
                )[0]
                representative_handles.setdefault(style["label"], line)

            _panel_label(ax, tokens=tokens, letter=chr(97 + panel_index))
            panel_index += 1

    legend_order = ["Steady-state GOH"] + [_study_style(label)["label"] for label in scenarios[0].study_legend]
    fig.legend(
        [representative_handles[label] for label in legend_order],
        legend_order,
        loc="center right",
        bbox_to_anchor=(0.99, 0.5),
        frameon=tokens["legend"]["frameon"],
        fontsize=fonts["legend_size_pt"],
    )
    fig.text(0.42, 0.955, spec["meta"]["title"], ha="center", va="center", fontsize=fonts["title_size_pt"] + 2, fontweight="bold")

    fig.savefig(file_paths["png"], dpi=dpi, transparent=spec["export"]["transparent"], facecolor=tokens["figure"]["background"])
    fig.savefig(file_paths["pdf"], dpi=dpi, transparent=spec["export"]["transparent"], facecolor=tokens["figure"]["background"])
    plt.close(fig)

    metadata = {
        "figure_id": figure_id,
        "source_mats": [str(scenario.source_mat_path) for scenario in scenarios],
        "legacy_digest_summary": digest_summary,
        "outputs": {key: str(value) for key, value in file_paths.items()},
    }
    file_paths["metadata"].write_text(json.dumps(metadata, indent=2), encoding="utf-8")

    return FigureBundleArtifacts(
        output_dir=output_dir,
        data_csv_path=file_paths["data_csv"],
        spec_copy_path=file_paths["spec_copy"],
        resolved_spec_path=file_paths["resolved_spec"],
        tokens_copy_path=file_paths["tokens_copy"],
        metadata_path=file_paths["metadata"],
        png_path=file_paths["png"],
        pdf_path=file_paths["pdf"],
    )


def render_sensitivity_figure_suite(
    *,
    legacy_example_dir: Path | None = None,
    output_dir: Path | None = None,
    compare_spec_path: Path | None = None,
    sensitivity_all_spec_path: Path | None = None,
    sensitivity_some_spec_path: Path | None = None,
) -> GOSMSensitivityFigureSuiteArtifacts:
    output_dir = (output_dir or DEFAULT_SENSITIVITY_OUTPUT_DIR).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    legacy_example_dir = (legacy_example_dir or DEFAULT_LEGACY_GOSM_EXAMPLE_DIR).resolve()

    compare_artifacts = render_compare_true_vs_imag_bundle(
        legacy_example_dir=legacy_example_dir,
        output_dir=output_dir / "compare_true_vs_imag",
        spec_path=compare_spec_path,
    )
    sensitivity_all_artifacts = render_sensitivity_all_bundle(
        legacy_example_dir=legacy_example_dir,
        output_dir=output_dir / "sensitivity_all",
        spec_path=sensitivity_all_spec_path,
    )
    sensitivity_some_artifacts = render_sensitivity_some_bundle(
        legacy_example_dir=legacy_example_dir,
        output_dir=output_dir / "sensitivity_some",
        spec_path=sensitivity_some_spec_path,
    )
    return GOSMSensitivityFigureSuiteArtifacts(
        compare_true_vs_imag=compare_artifacts,
        sensitivity_all=sensitivity_all_artifacts,
        sensitivity_some=sensitivity_some_artifacts,
    )
