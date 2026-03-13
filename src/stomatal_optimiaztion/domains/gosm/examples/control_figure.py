from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Any
import json
import warnings

import numpy as np
import pandas as pd
import yaml
from scipy.io import loadmat

from stomatal_optimiaztion.domains.gosm.model import (
    rad_hydr_grow_temp_cassimilation,
    steady_state_nsc_and_cue,
)
from stomatal_optimiaztion.domains.gosm.params import BaselineInputs

REPO_ROOT = Path(__file__).resolve().parents[5]
DEFAULT_CONTROL_FIGURE_SPEC_PATH = REPO_ROOT / "configs" / "plotkit" / "gosm" / "control_example_figure.yaml"
DEFAULT_CONTROL_FIGURE_OUTPUT_DIR = REPO_ROOT / "out" / "gosm" / "control_example"

LEGACY_CONTROL_DIGESTS = {
    "g_c_vec": "d58e2ea13f36a14c01a1e3a695877b0f3ef60ab77d474e30f8ce4995d3a34515",
    "panel_a_left": "402f2b8784ac0471b759adcfa9aa37b0194ac1444db8b8ce251f741abdfdbb3b",
    "panel_a_right": "791437f05d2f0f531a63761cda012005c3709f8798f691c9aacfbf01bc352bab",
    "panel_b_left": "ab66fc70bbdf0bd305b785824e53b427b6d17b53ffd351142a5ba6e957138419",
    "panel_c_left": "e01f1b2db5e35ce97dc625de806bb2e3817068eb9819bf96428b4517dff389e5",
    "panel_c_right": "913c0813a7b4ac9e5df4569dd4a25ab5a1475ebf96b64ac4ffe06d5c12d2dc6f",
    "panel_d_left": "2684d97d768be54d5fee9a288fa49c9c27550794f51a992cbb2e10f710fc187a",
}

LEGACY_CONTROL_DIGEST_DECIMALS = {
    "g_c_vec": 11,
    "panel_a_left": 8,
    "panel_a_right": 4,
    "panel_b_left": 12,
    "panel_c_left": 12,
    "panel_c_right": 12,
    "panel_d_left": 12,
}

PANEL_GROUPS: dict[str, tuple[str, ...]] = {
    "panel_a_left": ("g0_umol_c_s", "g_umol_c_s"),
    "panel_a_right": ("c_nsc_mol",),
    "panel_b_left": ("a_n_umol_m2_s", "e_mmol_m2_s"),
    "panel_c_left": ("t_l_c",),
    "panel_c_right": ("vpd_kpa",),
    "panel_d_left": ("neg_psi_l_mpa", "neg_psi_s_mpa", "neg_psi_rc_mpa"),
}


@dataclass(frozen=True)
class ExampleSeries:
    key: str
    values: np.ndarray


@dataclass(frozen=True)
class GOSMControlExamplePayload:
    g_c_vec: np.ndarray
    g_c_opt: float
    x_limit_max: float
    series: tuple[ExampleSeries, ...]

    def series_array(self, key: str) -> np.ndarray:
        for series in self.series:
            if series.key == key:
                return series.values
        raise KeyError(f"Unknown series key: {key}")

    def grouped_arrays(self) -> dict[str, np.ndarray]:
        grouped: dict[str, np.ndarray] = {}
        for group_name, keys in PANEL_GROUPS.items():
            grouped[group_name] = np.vstack([self.series_array(key) for key in keys])
        return grouped

    def optimal_index(self) -> int:
        return int(np.argmin(np.abs(self.g_c_vec - self.g_c_opt)))

    def to_long_frame(self) -> pd.DataFrame:
        records: list[dict[str, Any]] = []
        for group_name, keys in PANEL_GROUPS.items():
            panel_id, axis_name = group_name.rsplit("_", maxsplit=1)
            for key in keys:
                values = self.series_array(key)
                for g_c, value in zip(self.g_c_vec, values, strict=True):
                    records.append(
                        {
                            "panel_id": panel_id,
                            "axis": axis_name,
                            "series_key": key,
                            "g_c": float(g_c),
                            "value": float(value),
                        }
                    )
        return pd.DataFrame.from_records(records)


@dataclass(frozen=True)
class GOSMControlExampleFigureArtifacts:
    output_dir: Path
    data_csv_path: Path
    spec_copy_path: Path
    resolved_spec_path: Path
    tokens_copy_path: Path
    metadata_path: Path
    png_path: Path
    pdf_path: Path

    def to_summary(self) -> dict[str, Any]:
        return {
            "output_dir": str(self.output_dir),
            "data_csv": str(self.data_csv_path),
            "spec_copy": str(self.spec_copy_path),
            "resolved_spec": str(self.resolved_spec_path),
            "tokens_copy": str(self.tokens_copy_path),
            "metadata": str(self.metadata_path),
            "png": str(self.png_path),
            "pdf": str(self.pdf_path),
        }


def _normalize_digest_array(values: np.ndarray, *, decimals: int) -> np.ndarray:
    normalized = np.asarray(values, dtype=float)
    normalized = np.where(np.isnan(normalized), np.inf, normalized)
    return np.round(normalized, decimals)


def _digest_array(values: np.ndarray, *, decimals: int) -> str:
    return sha256(_normalize_digest_array(values, decimals=decimals).tobytes()).hexdigest()


def _leaf_water_potential(e_vec: np.ndarray, psi_s_vec: np.ndarray, *, inputs: BaselineInputs) -> np.ndarray:
    alpha_l = inputs.alpha_l
    beta_l = inputs.beta_l
    k_l = inputs.k_l

    with np.errstate(divide="ignore", invalid="ignore", over="ignore"):
        psi_l_vec = psi_s_vec - e_vec / k_l + beta_l + (1 / alpha_l) * np.log(
            np.exp(-alpha_l * beta_l)
            + np.exp(-alpha_l * psi_s_vec)
            - np.exp(-alpha_l * psi_s_vec + alpha_l * e_vec / k_l)
        )

    psi_l_vec = np.real(psi_l_vec)
    psi_l_vec[~np.isfinite(psi_l_vec)] = -np.inf
    return psi_l_vec


def build_control_example_payload(*, inputs: BaselineInputs | None = None) -> GOSMControlExamplePayload:
    inputs = inputs or BaselineInputs.matlab_default()
    e_vec = np.arange(0.0, 1e-2 + 1e-5, 1e-5)

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        (
            e_vec,
            a_n_vec,
            _r_d_vec,
            g0_vec,
            _g_w_vec,
            g_c_vec,
            lambda_wue_vec,
            d_g0_d_e_vec,
            _d_g0_d_g_c_vec,
            psi_s_vec,
            psi_rc_vec,
            t_l_vec,
            vpd_vec,
            *_,
        ) = rad_hydr_grow_temp_cassimilation(e_vec, inputs=inputs)

        (
            _a_n,
            _e,
            _lambda_wue,
            _g0,
            _g_c,
            _psi_s,
            _psi_rc,
            _eta_ss_vec,
            _lambda_wue_ss_vec,
            _c_nsc_ss,
            _r_m_0,
            _vpd,
            _eta_ss,
            c_nsc_ss_vec,
        ) = steady_state_nsc_and_cue(
            inputs=inputs,
            lambda_wue_vec=lambda_wue_vec,
            g0_vec=g0_vec,
            d_g0_d_e_vec=d_g0_d_e_vec,
            a_n_vec=a_n_vec,
            e_vec=e_vec,
            g_c_vec=g_c_vec,
            vpd_vec=vpd_vec,
            psi_s_vec=psi_s_vec,
            psi_rc_vec=psi_rc_vec,
        )

    psi_l_vec = _leaf_water_potential(e_vec, psi_s_vec, inputs=inputs)
    g_vec = g0_vec * inputs.theta_g(c_nsc_ss_vec)

    g_c_opt = float(g_c_vec[int(np.nanargmax(g_vec))])
    x_limit_max = float(np.floor(10 * np.nanmax(g_c_vec[psi_l_vec > -np.inf])) / 10)

    series = (
        ExampleSeries("g0_umol_c_s", 1e6 * g0_vec),
        ExampleSeries("g_umol_c_s", 1e6 * g_vec),
        ExampleSeries("c_nsc_mol", c_nsc_ss_vec),
        ExampleSeries("a_n_umol_m2_s", 1e6 * a_n_vec),
        ExampleSeries("e_mmol_m2_s", 1e3 * e_vec),
        ExampleSeries("t_l_c", t_l_vec),
        ExampleSeries("vpd_kpa", vpd_vec),
        ExampleSeries("neg_psi_l_mpa", -psi_l_vec),
        ExampleSeries("neg_psi_s_mpa", -psi_s_vec),
        ExampleSeries("neg_psi_rc_mpa", -psi_rc_vec),
    )
    return GOSMControlExamplePayload(
        g_c_vec=g_c_vec,
        g_c_opt=g_c_opt,
        x_limit_max=x_limit_max,
        series=series,
    )


def legacy_control_digest_summary(payload: GOSMControlExamplePayload) -> dict[str, Any]:
    current_digests = {
        "g_c_vec": _digest_array(payload.g_c_vec, decimals=LEGACY_CONTROL_DIGEST_DECIMALS["g_c_vec"])
    }
    current_digests.update(
        {
            name: _digest_array(values, decimals=LEGACY_CONTROL_DIGEST_DECIMALS[name])
            for name, values in payload.grouped_arrays().items()
        }
    )
    mismatches = {
        key: {"expected": expected, "actual": current_digests.get(key)}
        for key, expected in LEGACY_CONTROL_DIGESTS.items()
        if current_digests.get(key) != expected
    }
    return {
        "passed": not mismatches,
        "expected_digests": deepcopy(LEGACY_CONTROL_DIGESTS),
        "actual_digests": current_digests,
        "mismatches": mismatches,
    }


def compare_control_example_to_legacy_mat(
    payload: GOSMControlExamplePayload,
    *,
    legacy_mat_path: Path,
) -> dict[str, Any]:
    mat = loadmat(legacy_mat_path)
    ref_g_c_vec = np.asarray(mat["g_c_vect"], dtype=float).reshape(-1)
    ref_y_plot = mat["Y_plot_data"]

    mapping = {
        "panel_a_left": np.asarray(ref_y_plot[0, 0], dtype=float),
        "panel_a_right": np.asarray(ref_y_plot[0, 1], dtype=float),
        "panel_b_left": np.asarray(ref_y_plot[1, 0], dtype=float),
        "panel_c_left": np.asarray(ref_y_plot[2, 0], dtype=float),
        "panel_c_right": np.asarray(ref_y_plot[2, 1], dtype=float),
        "panel_d_left": np.asarray(ref_y_plot[3, 0], dtype=float),
    }

    result: dict[str, Any] = {
        "g_c_vec": {
            "same_shape": ref_g_c_vec.shape == payload.g_c_vec.shape,
            "max_abs_diff": float(np.max(np.abs(ref_g_c_vec - payload.g_c_vec))),
            "digest_match": _digest_array(
                ref_g_c_vec,
                decimals=LEGACY_CONTROL_DIGEST_DECIMALS["g_c_vec"],
            )
            == _digest_array(payload.g_c_vec, decimals=LEGACY_CONTROL_DIGEST_DECIMALS["g_c_vec"]),
        }
    }

    for name, ref_values in mapping.items():
        cur_values = payload.grouped_arrays()[name]
        ref_normalized = np.where(np.isnan(ref_values), np.inf, ref_values)
        cur_normalized = np.where(np.isnan(cur_values), np.inf, cur_values)
        finite_mask = np.isfinite(ref_normalized) & np.isfinite(cur_normalized)
        same_nonfinite = bool(np.array_equal(np.isinf(ref_normalized), np.isinf(cur_normalized)))
        result[name] = {
            "same_shape": ref_values.shape == cur_values.shape,
            "same_nonfinite": same_nonfinite,
            "max_abs_diff": float(np.max(np.abs(ref_normalized[finite_mask] - cur_normalized[finite_mask])))
            if finite_mask.any()
            else 0.0,
            "digest_match": _digest_array(ref_values, decimals=LEGACY_CONTROL_DIGEST_DECIMALS[name])
            == _digest_array(cur_values, decimals=LEGACY_CONTROL_DIGEST_DECIMALS[name]),
        }
    return result


def _load_yaml(path: Path) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _apply_axis_theme(ax: Any, *, tokens: dict[str, Any], show_xlabels: bool) -> None:
    axes_tokens = tokens["axes"]
    ax.set_facecolor(tokens["figure"]["background"])
    ax.grid(axis=axes_tokens.get("grid_major", "y"), color=axes_tokens["grid_color"], linewidth=axes_tokens["grid_width_pt"], alpha=axes_tokens["grid_alpha"])
    ax.tick_params(
        direction=axes_tokens["tick_direction"],
        length=axes_tokens["tick_length_pt"],
        width=axes_tokens["tick_width_pt"],
        colors=axes_tokens["tick_color"],
        labelsize=tokens["fonts"]["base_size_pt"],
    )
    for side in ("left", "right", "top", "bottom"):
        spine = ax.spines[side]
        spine.set_color(axes_tokens["spine_color"])
        spine.set_linewidth(axes_tokens["spine_width_pt"])
    if not show_xlabels:
        ax.tick_params(labelbottom=False)


def _resolve_figure_paths(output_dir: Path, figure_id: str) -> dict[str, Path]:
    return {
        "data_csv": output_dir / f"{figure_id}_data.csv",
        "spec_copy": output_dir / f"{figure_id}_spec.yaml",
        "resolved_spec": output_dir / f"{figure_id}_resolved_spec.yaml",
        "tokens_copy": output_dir / f"{figure_id}_tokens.yaml",
        "metadata": output_dir / f"{figure_id}_metadata.json",
        "png": output_dir / f"{figure_id}.png",
        "pdf": output_dir / f"{figure_id}.pdf",
    }


def render_control_example_figure_bundle(
    *,
    output_dir: Path | None = None,
    spec_path: Path | None = None,
    legacy_mat_path: Path | None = None,
    inputs: BaselineInputs | None = None,
) -> GOSMControlExampleFigureArtifacts:
    try:
        import matplotlib.pyplot as plt
    except ImportError as exc:  # pragma: no cover - protected by dependency lock
        raise RuntimeError("matplotlib is required to render the GOSM control example figure") from exc

    output_dir = (output_dir or DEFAULT_CONTROL_FIGURE_OUTPUT_DIR).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    spec_path = (spec_path or DEFAULT_CONTROL_FIGURE_SPEC_PATH).resolve()
    spec = _load_yaml(spec_path)
    tokens_path = (spec_path.parent / spec["theme"]["tokens"]).resolve()
    tokens = _load_yaml(tokens_path)
    payload = build_control_example_payload(inputs=inputs)
    digest_summary = legacy_control_digest_summary(payload)
    legacy_mat_comparison = (
        compare_control_example_to_legacy_mat(payload, legacy_mat_path=legacy_mat_path.resolve())
        if legacy_mat_path and legacy_mat_path.exists()
        else None
    )

    figure_id = spec["meta"]["id"]
    file_paths = _resolve_figure_paths(output_dir, figure_id)
    data_frame = payload.to_long_frame()

    resolved_spec = deepcopy(spec)
    resolved_spec["data"] = {
        "table_shape": "long",
        "path": str(file_paths["data_csv"]),
        "row_count": int(len(data_frame)),
        "columns": list(data_frame.columns),
    }
    resolved_spec["theme"]["resolved_tokens_path"] = str(tokens_path)
    resolved_spec["x_axis"]["resolved_limits"] = [0.0, payload.x_limit_max]
    resolved_spec["meta"]["legacy_digest_match"] = digest_summary["passed"]

    data_frame.to_csv(file_paths["data_csv"], index=False)
    file_paths["spec_copy"].write_text(spec_path.read_text(encoding="utf-8"), encoding="utf-8")
    file_paths["resolved_spec"].write_text(yaml.safe_dump(resolved_spec, sort_keys=False), encoding="utf-8")
    file_paths["tokens_copy"].write_text(tokens_path.read_text(encoding="utf-8"), encoding="utf-8")

    width_mm = float(spec["figure"]["width_mm"])
    height_mm = float(spec["figure"]["height_mm"])
    dpi = int(spec["export"]["dpi"])
    fig, axes = plt.subplots(
        nrows=len(spec["panels"]),
        ncols=1,
        figsize=(width_mm / 25.4, height_mm / 25.4),
        dpi=dpi,
        facecolor=tokens["figure"]["background"],
        constrained_layout=False,
    )
    fig.subplots_adjust(hspace=float(spec["layout"]["hspace"]), left=0.14, right=0.88, top=0.96, bottom=0.09)

    fonts = tokens["fonts"]
    highlight = spec["highlight"]
    idx_opt = payload.optimal_index()

    for idx, (ax, panel_spec) in enumerate(zip(np.atleast_1d(axes), spec["panels"], strict=True)):
        show_xlabels = idx == len(spec["panels"]) - 1
        _apply_axis_theme(ax, tokens=tokens, show_xlabels=show_xlabels)
        ax.set_xlim(0.0, payload.x_limit_max)
        ax.set_ylabel(panel_spec["left_axis"]["label"], fontsize=fonts["axis_label_size_pt"])
        ax.set_ylim(panel_spec["left_axis"]["limits"])
        ax.set_yscale(panel_spec["left_axis"]["scale"])

        left_handles = []
        left_labels = []
        for series_spec in panel_spec["left_axis"]["series"]:
            values = payload.series_array(series_spec["key"])
            line = ax.plot(
                payload.g_c_vec,
                values,
                color=series_spec["color"],
                linewidth=series_spec["linewidth_pt"],
                label=series_spec["label"],
            )[0]
            left_handles.append(line)
            left_labels.append(series_spec["label"])
            ax.scatter(
                [payload.g_c_opt],
                [values[idx_opt]],
                s=highlight["optimal_points"]["size_pt"] ** 2,
                facecolor=series_spec["color"],
                edgecolor=highlight["optimal_points"]["edgecolor"],
                linewidth=highlight["optimal_points"]["edgewidth_pt"],
                zorder=4,
            )

        ax.axvline(
            payload.g_c_opt,
            color=highlight["optimal_conductance"]["color"],
            linestyle=highlight["optimal_conductance"]["linestyle"],
            linewidth=highlight["optimal_conductance"]["linewidth_pt"],
        )
        ax.legend(
            left_handles,
            left_labels,
            loc=panel_spec["left_axis"]["legend_loc"],
            frameon=tokens["legend"]["frameon"],
            fontsize=fonts["legend_size_pt"],
            handlelength=tokens["legend"]["handlelength"],
            borderpad=tokens["legend"]["borderpad"],
        )

        if panel_spec.get("right_axis"):
            ax_right = ax.twinx()
            _apply_axis_theme(ax_right, tokens=tokens, show_xlabels=show_xlabels)
            ax_right.grid(False)
            ax_right.set_ylim(panel_spec["right_axis"]["limits"])
            ax_right.set_yscale(panel_spec["right_axis"]["scale"])
            ax_right.set_ylabel(panel_spec["right_axis"]["label"], fontsize=fonts["axis_label_size_pt"])

            right_handles = []
            right_labels = []
            for series_spec in panel_spec["right_axis"]["series"]:
                values = payload.series_array(series_spec["key"])
                line = ax_right.plot(
                    payload.g_c_vec,
                    values,
                    color=series_spec["color"],
                    linewidth=series_spec["linewidth_pt"],
                    label=series_spec["label"],
                )[0]
                right_handles.append(line)
                right_labels.append(series_spec["label"])
                ax_right.scatter(
                    [payload.g_c_opt],
                    [values[idx_opt]],
                    s=highlight["optimal_points"]["size_pt"] ** 2,
                    facecolor=series_spec["color"],
                    edgecolor=highlight["optimal_points"]["edgecolor"],
                    linewidth=highlight["optimal_points"]["edgewidth_pt"],
                    zorder=4,
                )
            ax_right.legend(
                right_handles,
                right_labels,
                loc=panel_spec["right_axis"]["legend_loc"],
                frameon=tokens["legend"]["frameon"],
                fontsize=fonts["legend_size_pt"],
                handlelength=tokens["legend"]["handlelength"],
                borderpad=tokens["legend"]["borderpad"],
            )

        if show_xlabels:
            ax.set_xlabel(spec["x_axis"]["label"], fontsize=fonts["axis_label_size_pt"])

        panel_tokens = tokens["panel_labels"]
        ax.text(
            panel_tokens["x"],
            panel_tokens["y"],
            f"{panel_tokens['prefix']}{panel_spec['id']}{panel_tokens['suffix']}",
            transform=ax.transAxes,
            ha=panel_tokens["ha"],
            va=panel_tokens["va"],
            fontsize=fonts["panel_label_size_pt"],
            fontweight=fonts["weight_labels"],
        )
        ax.set_title(panel_spec["title"], fontsize=fonts["title_size_pt"], loc="left", pad=10)

    fig.savefig(file_paths["png"], dpi=dpi, transparent=spec["export"]["transparent"], facecolor=tokens["figure"]["background"])
    fig.savefig(file_paths["pdf"], dpi=dpi, transparent=spec["export"]["transparent"], facecolor=tokens["figure"]["background"])
    plt.close(fig)

    metadata = {
        "figure_id": figure_id,
        "g_c_opt": payload.g_c_opt,
        "x_limit_max": payload.x_limit_max,
        "legacy_digest_summary": digest_summary,
        "legacy_mat_comparison": legacy_mat_comparison,
        "outputs": {key: str(path) for key, path in file_paths.items()},
    }
    file_paths["metadata"].write_text(json.dumps(metadata, indent=2), encoding="utf-8")

    return GOSMControlExampleFigureArtifacts(
        output_dir=output_dir,
        data_csv_path=file_paths["data_csv"],
        spec_copy_path=file_paths["spec_copy"],
        resolved_spec_path=file_paths["resolved_spec"],
        tokens_copy_path=file_paths["tokens_copy"],
        metadata_path=file_paths["metadata"],
        png_path=file_paths["png"],
        pdf_path=file_paths["pdf"],
    )
