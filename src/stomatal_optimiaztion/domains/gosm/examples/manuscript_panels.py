from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from typing import Any
import json
import warnings

import numpy as np
import pandas as pd

from stomatal_optimiaztion.domains.gosm.examples._plotkit import (
    apply_axis_theme,
    frame_digest,
    load_yaml,
    resolve_figure_paths,
)
from stomatal_optimiaztion.domains.gosm.model import rad_hydr_grow_temp_cassimilation
from stomatal_optimiaztion.domains.gosm.params import BaselineInputs

REPO_ROOT = Path(__file__).resolve().parents[5]
DEFAULT_MANUSCRIPT_PANEL_SPEC_PATH = REPO_ROOT / "configs" / "plotkit" / "gosm" / "manuscript_panels.yaml"
DEFAULT_MANUSCRIPT_PANEL_OUTPUT_DIR = REPO_ROOT / "out" / "gosm" / "manuscript_panels"

EXPECTED_PANEL_DIGESTS: dict[str, str | None] = {
    "vulnerability_root": "b199cf6f5a2b09fc55bae5d66548f9699ec206f8cdfce3621e76cd0627cf2a02",
    "vulnerability_stem": "58aad62eba56c87dfb738af063969f69d32e3878e18957b282d98e5fc113d4d4",
    "vulnerability_leaf": "8eacd91ee8a2f068994ae8c0abdfcd2b298f6fc9166be35798f4ba868dbae7da",
    "photosynthesis_an_gc": "8de8c467c6e424c6df85490c2756efc59d6dba0d03aabecea7aadeca74edc608",
    "photosynthesis_an_ci": "19f453cdfa68e81c16550ac43a53d465e0480647648cce769707cf4e56b27294",
    "growth_rm_c": "7b4bd6b451f5d8a51207b05266729d01c177da315f4200746e1dfef6edcaa2fa",
    "growth_g_c": "c49392b1d0b281a8b0a0e406aa2c64e58ef0912312c3b7a251060499a2df2c65",
    "growth_g_ta": "c0e310df7a973149c819508fdc4c973e1a13bccaaac86a7ddd054da335ec1f72",
    "growth_g_e": "5382949f218480f3dbfa2e5c07ef2666ced8e25be566774c3f46aa99849c23dd",
}


@dataclass(frozen=True)
class GOSMManuscriptPanelArtifacts:
    output_dir: Path
    data_csv_path: Path
    manifest_csv_path: Path
    spec_copy_path: Path
    resolved_spec_path: Path
    tokens_copy_path: Path
    metadata_path: Path
    overview_png_path: Path
    overview_pdf_path: Path
    panel_dir: Path

    def to_summary(self) -> dict[str, Any]:
        return {
            "output_dir": str(self.output_dir),
            "data_csv": str(self.data_csv_path),
            "manifest_csv": str(self.manifest_csv_path),
            "spec_copy": str(self.spec_copy_path),
            "resolved_spec": str(self.resolved_spec_path),
            "tokens_copy": str(self.tokens_copy_path),
            "metadata": str(self.metadata_path),
            "overview_png": str(self.overview_png_path),
            "overview_pdf": str(self.overview_pdf_path),
            "panel_dir": str(self.panel_dir),
        }


def _vulnerability_curve(psi: np.ndarray, *, alpha: float, beta: float) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-alpha * (psi - beta)))


def build_manuscript_panel_frame(*, inputs: BaselineInputs | None = None) -> pd.DataFrame:
    inputs = inputs or BaselineInputs.matlab_default()
    records: list[dict[str, Any]] = []

    x_potential = np.arange(0.0, 12.0 + 0.01, 0.01)
    psi_values = -x_potential
    vulnerability_panels = {
        "vulnerability_root": ("THORP-like vulnerability: root", "vulnerability_curve__belowground", _vulnerability_curve(psi_values, alpha=inputs.alpha_r, beta=inputs.beta_r)),
        "vulnerability_stem": ("THORP-like vulnerability: stem", "vulnerability_curve__stem", _vulnerability_curve(psi_values, alpha=inputs.alpha_sw, beta=inputs.beta_sw)),
        "vulnerability_leaf": ("THORP-like vulnerability: leaf", "vulnerability_curve__leaf", _vulnerability_curve(psi_values, alpha=inputs.alpha_l, beta=inputs.beta_l)),
    }
    for panel_id, (title, export_name, y_values) in vulnerability_panels.items():
        for x_value, y_value in zip(x_potential, y_values, strict=True):
            records.append(
                {
                    "panel_id": panel_id,
                    "panel_group": "vulnerability",
                    "title": title,
                    "legacy_export_name": export_name,
                    "x": float(x_value),
                    "y": float(y_value),
                }
            )

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
            _lambda_wue_vec,
            _d_g0_d_e_vec,
            _d_g0_d_g_c_vec,
            _psi_s_vec,
            _psi_rc_vec,
            _t_l_vec,
            _vpd_vec,
            *_,
        ) = rad_hydr_grow_temp_cassimilation(e_vec, inputs=inputs)
    with np.errstate(divide="ignore", invalid="ignore"):
        c_i_vec = inputs.c_a - a_n_vec / g_c_vec

    g_c_max_plot = 0.05 * np.nanmax(g_c_vec)
    valid_idx = np.where(g_c_vec <= g_c_max_plot)[0]
    idx_max = int(valid_idx.max()) if valid_idx.size else len(g_c_vec) - 1

    photosynthesis_panels = {
        "photosynthesis_an_gc": ("A_n versus g_c", "A_n--g_c", g_c_vec[: idx_max + 1] / np.nanmax(g_c_vec[: idx_max + 1]), a_n_vec[: idx_max + 1] / np.nanmax(a_n_vec[: idx_max + 1])),
        "photosynthesis_an_ci": ("A_n versus c_i", "A_n--c_i", c_i_vec[: idx_max + 1] / np.nanmax(c_i_vec[: idx_max + 1]), a_n_vec[: idx_max + 1] / np.nanmax(a_n_vec[: idx_max + 1])),
    }
    for panel_id, (title, export_name, x_values, y_values) in photosynthesis_panels.items():
        for x_value, y_value in zip(x_values, y_values, strict=True):
            records.append(
                {
                    "panel_id": panel_id,
                    "panel_group": "photosynthesis",
                    "title": title,
                    "legacy_export_name": export_name,
                    "x": float(x_value),
                    "y": float(y_value),
                }
            )

    c_values = np.arange(0.0, 2.0 + 0.01, 0.01)
    t_a_values = np.arange(0.0, 40.0 + 0.1, 0.1)
    g_t_values = inputs.phi_extens_effective(t_a_values)
    e_max_plot = min(e_vec[g0_vec == 0]) if np.any(g0_vec == 0) else 0.75 * np.nanmax(e_vec)
    e_max_plot = 0.75 * e_max_plot + 0.25 * np.nanmax(e_vec)
    valid_g0_idx = np.where(e_vec <= e_max_plot)[0]
    idx_g0 = int(valid_g0_idx.max()) if valid_g0_idx.size else len(e_vec) - 1

    growth_panels = {
        "growth_rm_c": ("R_M versus C", "R_M--C", c_values / np.nanmax(c_values), c_values / (c_values + inputs.gamma_r)),
        "growth_g_c": ("G versus C", "G--C", c_values / np.nanmax(c_values), c_values / (c_values + inputs.gamma_g)),
        "growth_g_ta": ("G versus T_a", "G--T_a", t_a_values / np.nanmax(t_a_values), g_t_values / np.nanmax(g_t_values)),
        "growth_g_e": ("G versus E", "G--E", e_vec[: idx_g0 + 1] / np.nanmax(e_vec[: idx_g0 + 1]), g0_vec[: idx_g0 + 1] / np.nanmax(g0_vec[: idx_g0 + 1])),
    }
    for panel_id, (title, export_name, x_values, y_values) in growth_panels.items():
        for x_value, y_value in zip(x_values, y_values, strict=True):
            records.append(
                {
                    "panel_id": panel_id,
                    "panel_group": "growth",
                    "title": title,
                    "legacy_export_name": export_name,
                    "x": float(x_value),
                    "y": float(y_value),
                }
            )

    return pd.DataFrame.from_records(records)


def render_manuscript_panel_bundle(
    *,
    output_dir: Path | None = None,
    spec_path: Path | None = None,
    inputs: BaselineInputs | None = None,
) -> GOSMManuscriptPanelArtifacts:
    import matplotlib.pyplot as plt

    output_dir = (output_dir or DEFAULT_MANUSCRIPT_PANEL_OUTPUT_DIR).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    panel_dir = output_dir / "panels"
    panel_dir.mkdir(parents=True, exist_ok=True)
    spec_path = (spec_path or DEFAULT_MANUSCRIPT_PANEL_SPEC_PATH).resolve()

    spec = load_yaml(spec_path)
    tokens_path = (spec_path.parent / spec["theme"]["tokens"]).resolve()
    tokens = load_yaml(tokens_path)
    frame = build_manuscript_panel_frame(inputs=inputs)
    figure_id = spec["meta"]["id"]
    file_paths = resolve_figure_paths(output_dir, figure_id)
    manifest_csv_path = output_dir / f"{figure_id}_manifest.csv"

    digest_summary = {
        panel_id: {
            "expected": EXPECTED_PANEL_DIGESTS[panel_id],
            "actual": frame_digest(frame[frame["panel_id"] == panel_id][["x", "y"]]),
            "passed": None if EXPECTED_PANEL_DIGESTS[panel_id] is None else EXPECTED_PANEL_DIGESTS[panel_id] == frame_digest(frame[frame["panel_id"] == panel_id][["x", "y"]]),
        }
        for panel_id in spec["panel_order"]
    }
    overall_passed = None if any(value["passed"] is None for value in digest_summary.values()) else all(
        bool(value["passed"]) for value in digest_summary.values()
    )

    resolved_spec = deepcopy(spec)
    resolved_spec["data"] = {
        "path": str(file_paths["data_csv"]),
        "row_count": int(len(frame)),
        "columns": list(frame.columns),
    }
    resolved_spec["meta"]["legacy_digest_match"] = overall_passed

    frame.to_csv(file_paths["data_csv"], index=False)
    manifest = (
        frame[["panel_id", "panel_group", "title", "legacy_export_name"]]
        .drop_duplicates()
        .sort_values(["panel_group", "panel_id"])
        .reset_index(drop=True)
    )
    manifest.to_csv(manifest_csv_path, index=False)
    file_paths["spec_copy"].write_text(spec_path.read_text(encoding="utf-8"), encoding="utf-8")
    file_paths["resolved_spec"].write_text(json.dumps(resolved_spec, indent=2), encoding="utf-8")
    file_paths["tokens_copy"].write_text(tokens_path.read_text(encoding="utf-8"), encoding="utf-8")

    width_mm = float(spec["figure"]["width_mm"])
    height_mm = float(spec["figure"]["height_mm"])
    dpi = int(spec["export"]["dpi"])
    fig, axes = plt.subplots(
        spec["layout"]["rows"],
        spec["layout"]["cols"],
        figsize=(width_mm / 25.4, height_mm / 25.4),
        dpi=dpi,
        facecolor=tokens["figure"]["background"],
        constrained_layout=False,
    )
    fig.subplots_adjust(left=0.08, right=0.98, bottom=0.08, top=0.94, wspace=0.26, hspace=0.34)
    fonts = tokens["fonts"]

    for ax, panel_id, letter in zip(axes.reshape(-1), spec["panel_order"], "abcdefghi", strict=True):
        panel_spec = spec["panels"][panel_id]
        panel_frame = frame[frame["panel_id"] == panel_id].sort_values("x")
        apply_axis_theme(ax, tokens=tokens, show_xlabels=True)
        ax.set_xlim(panel_spec["x_limits"])
        ax.set_ylim(panel_spec["y_limits"])
        ax.plot(
            panel_frame["x"],
            panel_frame["y"],
            color=panel_spec["color"],
            linewidth=panel_spec["linewidth_pt"],
        )
        ax.set_xlabel(panel_spec["x_label"], fontsize=fonts["axis_label_size_pt"])
        ax.set_ylabel(panel_spec["y_label"], fontsize=fonts["axis_label_size_pt"])
        ax.set_title(panel_spec["title"], fontsize=fonts["title_size_pt"], loc="left", pad=6)
        panel_tokens = tokens["panel_labels"]
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

        panel_fig, panel_ax = plt.subplots(
            1,
            1,
            figsize=(panel_spec["panel_width_mm"] / 25.4, panel_spec["panel_height_mm"] / 25.4),
            dpi=dpi,
            facecolor=tokens["figure"]["background"],
            constrained_layout=False,
        )
        panel_fig.subplots_adjust(left=0.20, right=0.97, bottom=0.20, top=0.92)
        apply_axis_theme(panel_ax, tokens=tokens, show_xlabels=True)
        panel_ax.set_xlim(panel_spec["x_limits"])
        panel_ax.set_ylim(panel_spec["y_limits"])
        panel_ax.plot(
            panel_frame["x"],
            panel_frame["y"],
            color=panel_spec["color"],
            linewidth=panel_spec["linewidth_pt"],
        )
        panel_ax.set_xlabel(panel_spec["x_label"], fontsize=fonts["axis_label_size_pt"])
        panel_ax.set_ylabel(panel_spec["y_label"], fontsize=fonts["axis_label_size_pt"])
        stem = panel_spec["legacy_export_name"]
        panel_png_path = panel_dir / f"{stem}.png"
        panel_pdf_path = panel_dir / f"{stem}.pdf"
        panel_fig.savefig(panel_png_path, dpi=dpi, transparent=spec["export"]["transparent"], facecolor=tokens["figure"]["background"])
        panel_fig.savefig(panel_pdf_path, dpi=dpi, transparent=spec["export"]["transparent"], facecolor=tokens["figure"]["background"])
        plt.close(panel_fig)

    fig.savefig(file_paths["png"], dpi=dpi, transparent=spec["export"]["transparent"], facecolor=tokens["figure"]["background"])
    fig.savefig(file_paths["pdf"], dpi=dpi, transparent=spec["export"]["transparent"], facecolor=tokens["figure"]["background"])
    plt.close(fig)

    metadata = {
        "figure_id": figure_id,
        "legacy_digest_summary": {
            "overall_passed": overall_passed,
            "panels": digest_summary,
        },
        "outputs": {
            "overview_png": str(file_paths["png"]),
            "overview_pdf": str(file_paths["pdf"]),
            "data_csv": str(file_paths["data_csv"]),
            "manifest_csv": str(manifest_csv_path),
            "spec_copy": str(file_paths["spec_copy"]),
            "resolved_spec": str(file_paths["resolved_spec"]),
            "tokens_copy": str(file_paths["tokens_copy"]),
            "metadata": str(file_paths["metadata"]),
            "panel_dir": str(panel_dir),
        },
    }
    file_paths["metadata"].write_text(json.dumps(metadata, indent=2), encoding="utf-8")

    return GOSMManuscriptPanelArtifacts(
        output_dir=output_dir,
        data_csv_path=file_paths["data_csv"],
        manifest_csv_path=manifest_csv_path,
        spec_copy_path=file_paths["spec_copy"],
        resolved_spec_path=file_paths["resolved_spec"],
        tokens_copy_path=file_paths["tokens_copy"],
        metadata_path=file_paths["metadata"],
        overview_png_path=file_paths["png"],
        overview_pdf_path=file_paths["pdf"],
        panel_dir=panel_dir,
    )
