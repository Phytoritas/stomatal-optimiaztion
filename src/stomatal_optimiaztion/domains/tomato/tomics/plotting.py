from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import yaml

from stomatal_optimiaztion.shared_plotkit import (
    FigureBundleArtifacts,
    apply_axis_theme,
    frame_digest,
    load_yaml,
    resolve_figure_paths,
)

_PANEL_LETTERS = "abcdefghijklmnopqrstuvwxyz"


def _require_matplotlib() -> tuple[Any, Any]:
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.dates as mdates
        import matplotlib.pyplot as plt
    except ModuleNotFoundError as exc:  # pragma: no cover
        raise ModuleNotFoundError("Plotkit-style rendering requires matplotlib.") from exc
    return plt, mdates


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


def _y_limits(
    values: np.ndarray,
    *,
    explicit_limits: list[float] | tuple[float, float] | None = None,
    padding_fraction: float = 0.08,
) -> tuple[float, float]:
    if explicit_limits is not None:
        return float(explicit_limits[0]), float(explicit_limits[1])
    finite = values[np.isfinite(values)]
    if finite.size == 0:
        return 0.0, 1.0
    y_min = float(np.nanmin(finite))
    y_max = float(np.nanmax(finite))
    if np.isclose(y_min, y_max):
        baseline = abs(y_min) if y_min != 0.0 else 1.0
        return y_min - baseline * padding_fraction, y_max + baseline * padding_fraction
    pad = (y_max - y_min) * padding_fraction
    return y_min - pad, y_max + pad


def _prepare_bundle(
    *,
    spec_path: Path,
    out_path: Path,
    label_overrides: dict[str, str] | None = None,
) -> tuple[dict[str, Any], dict[str, Any], Path, dict[str, Path]]:
    output_dir = out_path.resolve().parent
    output_dir.mkdir(parents=True, exist_ok=True)
    spec = copy.deepcopy(load_yaml(spec_path.resolve()))
    spec.setdefault("meta", {})
    spec["meta"]["id"] = out_path.stem
    if label_overrides:
        for source_name, label in label_overrides.items():
            styling = spec.setdefault("styling", {}).setdefault("sources", {})
            if source_name in styling:
                styling[source_name]["label"] = label
    tokens_path = (spec_path.resolve().parent / spec["theme"]["tokens"]).resolve()
    tokens = load_yaml(tokens_path)
    file_paths = resolve_figure_paths(output_dir, str(spec["meta"]["id"]))
    return spec, tokens, tokens_path, file_paths


def _serialize_frame(frame: pd.DataFrame) -> pd.DataFrame:
    serialized = frame.copy()
    for column in serialized.columns:
        if pd.api.types.is_datetime64_any_dtype(serialized[column]):
            serialized[column] = serialized[column].dt.strftime("%Y-%m-%dT%H:%M:%S")
    return serialized


def _write_bundle_sidecars(
    *,
    spec_path: Path,
    spec: dict[str, Any],
    tokens_path: Path,
    file_paths: dict[str, Path],
    data_frame: pd.DataFrame,
    extra_metadata: dict[str, Any] | None = None,
) -> None:
    serialized = _serialize_frame(data_frame)
    serialized.to_csv(file_paths["data_csv"], index=False)
    file_paths["spec_copy"].write_text(spec_path.resolve().read_text(encoding="utf-8"), encoding="utf-8")
    file_paths["resolved_spec"].write_text(
        yaml.safe_dump(spec, sort_keys=False, allow_unicode=False),
        encoding="utf-8",
    )
    file_paths["tokens_copy"].write_text(tokens_path.read_text(encoding="utf-8"), encoding="utf-8")
    metadata = {
        "figure_id": spec["meta"]["id"],
        "title": spec["meta"].get("title", spec["meta"]["id"]),
        "spec_path": str(spec_path.resolve()),
        "tokens_path": str(tokens_path),
        "data_csv": str(file_paths["data_csv"]),
        "frame_digest": frame_digest(serialized),
        "rows": int(serialized.shape[0]),
    }
    if extra_metadata:
        metadata.update(extra_metadata)
    file_paths["metadata"].write_text(
        json.dumps(metadata, indent=2, sort_keys=True),
        encoding="utf-8",
    )


def _save_bundle_figure(
    *,
    fig: Any,
    spec: dict[str, Any],
    tokens: dict[str, Any],
    file_paths: dict[str, Path],
) -> FigureBundleArtifacts:
    export_cfg = spec.get("export", {})
    dpi = int(export_cfg.get("dpi", tokens.get("figure", {}).get("default_dpi", 300)))
    formats = {str(fmt) for fmt in export_cfg.get("formats", ["png"])}
    transparent = bool(export_cfg.get("transparent", False))
    fig.savefig(
        file_paths["png"],
        dpi=dpi,
        transparent=transparent,
        facecolor=tokens["figure"]["background"],
    )
    pdf_path: Path | None = None
    if "pdf" in formats:
        fig.savefig(
            file_paths["pdf"],
            dpi=dpi,
            transparent=transparent,
            facecolor=tokens["figure"]["background"],
        )
        pdf_path = file_paths["pdf"]
    plt, _ = _require_matplotlib()
    plt.close(fig)
    return FigureBundleArtifacts(
        output_dir=file_paths["png"].parent,
        png_path=file_paths["png"],
        data_csv_path=file_paths["data_csv"],
        spec_copy_path=file_paths["spec_copy"],
        resolved_spec_path=file_paths["resolved_spec"],
        tokens_copy_path=file_paths["tokens_copy"],
        metadata_path=file_paths["metadata"],
        pdf_path=pdf_path,
    )


def _apply_secondary_axis_style(ax: Any, *, tokens: dict[str, Any]) -> None:
    axes_tokens = tokens["axes"]
    ax.tick_params(
        direction=axes_tokens["tick_direction"],
        length=axes_tokens["tick_length_pt"],
        width=axes_tokens["tick_width_pt"],
        colors=axes_tokens["tick_color"],
        labelsize=tokens["fonts"]["base_size_pt"],
    )
    for side in ("right", "top"):
        spine = ax.spines[side]
        spine.set_color(axes_tokens["spine_color"])
        spine.set_linewidth(axes_tokens["spine_width_pt"])
    ax.spines["left"].set_visible(False)
    ax.grid(False)


def _figure_size(spec: dict[str, Any]) -> tuple[float, float]:
    return (
        float(spec["figure"]["width_mm"]) / 25.4,
        float(spec["figure"]["height_mm"]) / 25.4,
    )


def render_partition_compare_bundle(
    *,
    runs: dict[str, pd.DataFrame],
    out_path: Path,
    spec_path: Path,
) -> FigureBundleArtifacts:
    plt, mdates = _require_matplotlib()
    spec, tokens, tokens_path, file_paths = _prepare_bundle(spec_path=spec_path, out_path=out_path)

    records: list[pd.DataFrame] = []
    for panel_id in spec["panel_order"]:
        panel_spec = spec["panels"][panel_id]
        column = str(panel_spec["column"])
        for source_name, df in runs.items():
            if "datetime" not in df.columns or column not in df.columns:
                continue
            records.append(
                pd.DataFrame(
                    {
                        "panel_id": panel_id,
                        "source": source_name,
                        "datetime": pd.to_datetime(df["datetime"]),
                        "value": pd.to_numeric(df[column], errors="coerce"),
                    }
                )
            )
    if not records:
        raise ValueError("No TOMICS partition-comparison data were available for Plotkit rendering.")
    frame = pd.concat(records, ignore_index=True)

    fig, axes = plt.subplots(
        spec["layout"]["rows"],
        spec["layout"]["cols"],
        figsize=_figure_size(spec),
        dpi=int(spec["export"]["dpi"]),
        facecolor=tokens["figure"]["background"],
        constrained_layout=False,
    )
    fig.subplots_adjust(
        left=0.11,
        right=0.98,
        bottom=0.12,
        top=0.88,
        hspace=float(spec["layout"]["hspace"]),
        wspace=float(spec["layout"]["wspace"]),
    )
    axes_vec = np.atleast_1d(axes).reshape(-1)
    handles: dict[str, Any] = {}
    fonts = tokens["fonts"]
    last_row_start = max((int(spec["layout"]["rows"]) - 1) * int(spec["layout"]["cols"]), 0)
    locator = mdates.AutoDateLocator(minticks=4, maxticks=8)

    for idx, panel_id in enumerate(spec["panel_order"]):
        ax = axes_vec[idx]
        panel_spec = spec["panels"][panel_id]
        show_xlabels = idx >= last_row_start
        apply_axis_theme(ax, tokens=tokens, show_xlabels=show_xlabels)
        panel_frame = frame[frame["panel_id"] == panel_id]
        ax.set_title(panel_spec["title"], fontsize=fonts["title_size_pt"], loc="left", pad=6)
        ax.set_ylabel(panel_spec["y_label"], fontsize=fonts["axis_label_size_pt"])
        ax.set_yscale(panel_spec.get("scale", "linear"))
        ax.xaxis.set_major_locator(locator)
        ax.xaxis.set_major_formatter(mdates.ConciseDateFormatter(locator))
        if show_xlabels:
            ax.set_xlabel(panel_spec["x_label"], fontsize=fonts["axis_label_size_pt"])
        ax.set_ylim(
            _y_limits(
                panel_frame["value"].to_numpy(dtype=float),
                explicit_limits=panel_spec.get("y_limits"),
                padding_fraction=float(panel_spec.get("y_padding_fraction", 0.08)),
            )
        )

        for source_name, style in spec["styling"]["sources"].items():
            source_frame = panel_frame[panel_frame["source"] == source_name].sort_values("datetime")
            if source_frame.empty:
                continue
            handle = ax.plot(
                source_frame["datetime"],
                source_frame["value"],
                color=style["color"],
                linestyle=style["linestyle"],
                marker=style.get("marker"),
                linewidth=float(style["linewidth_pt"]),
                label=style["label"],
            )[0]
            handles.setdefault(style["label"], handle)

        _panel_label(ax, tokens=tokens, letter=_PANEL_LETTERS[idx])

    for extra_ax in axes_vec[len(spec["panel_order"]) :]:
        extra_ax.set_visible(False)

    legend_order = [
        spec["styling"]["sources"][source_name]["label"]
        for source_name in spec["styling"]["sources"]
        if spec["styling"]["sources"][source_name]["label"] in handles
    ]
    fig.legend(
        [handles[label] for label in legend_order],
        legend_order,
        loc="upper center",
        bbox_to_anchor=(0.5, 0.955),
        ncol=max(1, len(legend_order)),
        frameon=tokens["legend"]["frameon"],
        fontsize=fonts["legend_size_pt"],
    )
    fig.suptitle(
        spec["meta"]["title"],
        x=0.5,
        y=0.985,
        fontsize=fonts["title_size_pt"] + 2,
        fontweight="bold",
    )

    _write_bundle_sidecars(
        spec_path=spec_path,
        spec=spec,
        tokens_path=tokens_path,
        file_paths=file_paths,
        data_frame=frame,
        extra_metadata={"sources": list(runs.keys()), "panel_count": len(spec["panel_order"])},
    )
    return _save_bundle_figure(fig=fig, spec=spec, tokens=tokens, file_paths=file_paths)


def render_factorial_summary_bundle(
    *,
    metrics_df: pd.DataFrame,
    out_path: Path,
    spec_path: Path,
) -> FigureBundleArtifacts:
    plt, _ = _require_matplotlib()
    spec, tokens, tokens_path, file_paths = _prepare_bundle(spec_path=spec_path, out_path=out_path)
    fig, axes = plt.subplots(
        spec["layout"]["rows"],
        spec["layout"]["cols"],
        figsize=_figure_size(spec),
        dpi=int(spec["export"]["dpi"]),
        facecolor=tokens["figure"]["background"],
        constrained_layout=False,
    )
    fig.subplots_adjust(
        left=0.10,
        right=0.98,
        bottom=0.16,
        top=0.87,
        hspace=float(spec["layout"]["hspace"]),
        wspace=float(spec["layout"]["wspace"]),
    )
    axes_vec = np.atleast_1d(axes).reshape(-1)
    fonts = tokens["fonts"]
    handles: dict[str, Any] = {}

    left_spec = spec["panels"]["factorial_outcomes"]
    ax = axes_vec[0]
    apply_axis_theme(ax, tokens=tokens, show_xlabels=True)
    ax.set_title(left_spec["title"], fontsize=fonts["title_size_pt"], loc="left", pad=6)
    ax.set_xlabel(left_spec["x_label"], fontsize=fonts["axis_label_size_pt"])
    ax.set_ylabel(left_spec["y_label"], fontsize=fonts["axis_label_size_pt"])
    for policy_name, style in spec["styling"]["sources"].items():
        group = metrics_df[metrics_df["partition_policy"] == policy_name]
        if group.empty:
            continue
        handle = ax.scatter(
            pd.to_numeric(group["final_lai"], errors="coerce"),
            pd.to_numeric(group["final_total_dry_weight_g_m2"], errors="coerce"),
            label=style["label"],
            color=style["color"],
            marker=style["marker"],
            alpha=0.85,
        )
        handles.setdefault(style["label"], handle)
    _panel_label(ax, tokens=tokens, letter=_PANEL_LETTERS[0])

    right_spec = spec["panels"]["root_moderation"]
    ax = axes_vec[1]
    apply_axis_theme(ax, tokens=tokens, show_xlabels=True)
    ax.set_title(right_spec["title"], fontsize=fonts["title_size_pt"], loc="left", pad=6)
    ax.set_xlabel(right_spec["x_label"], fontsize=fonts["axis_label_size_pt"])
    ax.set_ylabel(right_spec["y_label"], fontsize=fonts["axis_label_size_pt"])
    summary = (
        metrics_df.groupby(["partition_policy", "theta_substrate"], as_index=False)["mean_alloc_frac_root"]
        .mean()
        .sort_values(["theta_substrate", "partition_policy"])
    )
    for policy_name, style in spec["styling"]["sources"].items():
        group = summary[summary["partition_policy"] == policy_name]
        if group.empty:
            continue
        handle = ax.plot(
            group["theta_substrate"],
            group["mean_alloc_frac_root"],
            marker=style["marker"],
            linewidth=float(style["linewidth_pt"]),
            linestyle=style["linestyle"],
            color=style["color"],
            label=style["label"],
        )[0]
        handles.setdefault(style["label"], handle)
    _panel_label(ax, tokens=tokens, letter=_PANEL_LETTERS[1])

    legend_order = [style["label"] for style in spec["styling"]["sources"].values() if style["label"] in handles]
    fig.legend(
        [handles[label] for label in legend_order],
        legend_order,
        loc="upper center",
        bbox_to_anchor=(0.5, 0.97),
        ncol=max(1, len(legend_order)),
        frameon=tokens["legend"]["frameon"],
        fontsize=fonts["legend_size_pt"],
    )
    fig.suptitle(
        spec["meta"]["title"],
        x=0.5,
        y=0.99,
        fontsize=fonts["title_size_pt"] + 2,
        fontweight="bold",
    )

    _write_bundle_sidecars(
        spec_path=spec_path,
        spec=spec,
        tokens_path=tokens_path,
        file_paths=file_paths,
        data_frame=metrics_df,
        extra_metadata={"panel_count": 2},
    )
    return _save_bundle_figure(fig=fig, spec=spec, tokens=tokens, file_paths=file_paths)


def render_architecture_summary_bundle(
    *,
    metrics_df: pd.DataFrame,
    out_path: Path,
    spec_path: Path,
) -> FigureBundleArtifacts:
    plt, _ = _require_matplotlib()
    spec, tokens, tokens_path, file_paths = _prepare_bundle(spec_path=spec_path, out_path=out_path)
    fig, ax = plt.subplots(
        1,
        1,
        figsize=_figure_size(spec),
        dpi=int(spec["export"]["dpi"]),
        facecolor=tokens["figure"]["background"],
        constrained_layout=False,
    )
    fig.subplots_adjust(left=0.11, right=0.92, bottom=0.16, top=0.85)
    fonts = tokens["fonts"]
    panel_spec = spec["panels"]["architecture_score"]
    apply_axis_theme(ax, tokens=tokens, show_xlabels=True)
    scatter = ax.scatter(
        pd.to_numeric(metrics_df["final_fruit_dry_weight"], errors="coerce"),
        pd.to_numeric(metrics_df["score"], errors="coerce"),
        c=pd.to_numeric(metrics_df["canopy_collapse_days"], errors="coerce"),
        cmap=panel_spec.get("cmap", "viridis"),
        alpha=0.9,
    )
    ax.set_title(panel_spec["title"], fontsize=fonts["title_size_pt"], loc="left", pad=6)
    ax.set_xlabel(panel_spec["x_label"], fontsize=fonts["axis_label_size_pt"])
    ax.set_ylabel(panel_spec["y_label"], fontsize=fonts["axis_label_size_pt"])
    colorbar = fig.colorbar(scatter, ax=ax, fraction=0.045, pad=0.02)
    colorbar.set_label(panel_spec["colorbar_label"], fontsize=fonts["axis_label_size_pt"])
    _panel_label(ax, tokens=tokens, letter=_PANEL_LETTERS[0])
    fig.suptitle(
        spec["meta"]["title"],
        x=0.5,
        y=0.98,
        fontsize=fonts["title_size_pt"] + 2,
        fontweight="bold",
    )
    _write_bundle_sidecars(
        spec_path=spec_path,
        spec=spec,
        tokens_path=tokens_path,
        file_paths=file_paths,
        data_frame=metrics_df,
        extra_metadata={"panel_count": 1},
    )
    return _save_bundle_figure(fig=fig, spec=spec, tokens=tokens, file_paths=file_paths)


def render_main_effects_bundle(
    *,
    interactions_df: pd.DataFrame,
    out_path: Path,
    spec_path: Path,
) -> FigureBundleArtifacts:
    plt, _ = _require_matplotlib()
    spec, tokens, tokens_path, file_paths = _prepare_bundle(spec_path=spec_path, out_path=out_path)
    top_n = int(spec["panels"]["top_effects"].get("top_n", 12))
    top = interactions_df.sort_values("mean_score", ascending=False).head(top_n).copy()
    top["factor_level"] = [f"{row.factor}={row.level}" for row in top.itertuples(index=False)]

    fig, ax = plt.subplots(
        1,
        1,
        figsize=_figure_size(spec),
        dpi=int(spec["export"]["dpi"]),
        facecolor=tokens["figure"]["background"],
        constrained_layout=False,
    )
    fig.subplots_adjust(left=0.28, right=0.98, bottom=0.16, top=0.85)
    fonts = tokens["fonts"]
    panel_spec = spec["panels"]["top_effects"]
    apply_axis_theme(ax, tokens=tokens, show_xlabels=True)
    ax.barh(top["factor_level"], top["mean_score"], color=panel_spec.get("color", "#6D597A"))
    ax.set_title(panel_spec["title"], fontsize=fonts["title_size_pt"], loc="left", pad=6)
    ax.set_xlabel(panel_spec["x_label"], fontsize=fonts["axis_label_size_pt"])
    ax.set_ylabel(panel_spec["y_label"], fontsize=fonts["axis_label_size_pt"])
    ax.invert_yaxis()
    _panel_label(ax, tokens=tokens, letter=_PANEL_LETTERS[0])
    fig.suptitle(
        spec["meta"]["title"],
        x=0.5,
        y=0.98,
        fontsize=fonts["title_size_pt"] + 2,
        fontweight="bold",
    )
    _write_bundle_sidecars(
        spec_path=spec_path,
        spec=spec,
        tokens_path=tokens_path,
        file_paths=file_paths,
        data_frame=top,
        extra_metadata={"panel_count": 1, "top_n": top_n},
    )
    return _save_bundle_figure(fig=fig, spec=spec, tokens=tokens, file_paths=file_paths)


def render_simulation_summary_bundle(
    *,
    df: pd.DataFrame,
    out_path: Path,
    spec_path: Path,
) -> FigureBundleArtifacts:
    plt, mdates = _require_matplotlib()
    spec, tokens, tokens_path, file_paths = _prepare_bundle(spec_path=spec_path, out_path=out_path)
    fig, axes = plt.subplots(
        spec["layout"]["rows"],
        spec["layout"]["cols"],
        figsize=_figure_size(spec),
        dpi=int(spec["export"]["dpi"]),
        facecolor=tokens["figure"]["background"],
        constrained_layout=False,
    )
    fig.subplots_adjust(left=0.10, right=0.96, bottom=0.10, top=0.92, hspace=float(spec["layout"]["hspace"]))
    axes_vec = np.atleast_1d(axes).reshape(-1)
    fonts = tokens["fonts"]
    locator = mdates.AutoDateLocator(minticks=4, maxticks=10)
    work = df.copy()
    work["datetime"] = pd.to_datetime(work["datetime"])

    for idx, panel_id in enumerate(spec["panel_order"]):
        ax = axes_vec[idx]
        panel_spec = spec["panels"][panel_id]
        show_xlabels = idx == len(spec["panel_order"]) - 1
        apply_axis_theme(ax, tokens=tokens, show_xlabels=show_xlabels)
        ax.set_title(panel_spec["title"], fontsize=fonts["title_size_pt"], loc="left", pad=6)
        ax.xaxis.set_major_locator(locator)
        ax.xaxis.set_major_formatter(mdates.ConciseDateFormatter(locator))
        if show_xlabels:
            ax.set_xlabel(panel_spec["x_label"], fontsize=fonts["axis_label_size_pt"])

        primary = panel_spec["primary"]
        handles: list[Any] = []
        labels: list[str] = []
        if primary["series"]:
            primary_values: list[np.ndarray] = []
            for series_spec in primary["series"]:
                column = series_spec["column"]
                if column not in work.columns:
                    continue
                values = pd.to_numeric(work[column], errors="coerce")
                handle = ax.plot(
                    work["datetime"],
                    values,
                    color=series_spec["color"],
                    linewidth=float(series_spec["linewidth_pt"]),
                    label=series_spec["label"],
                )[0]
                handles.append(handle)
                labels.append(series_spec["label"])
                primary_values.append(values.to_numpy(dtype=float))
            ax.set_ylabel(primary["y_label"], fontsize=fonts["axis_label_size_pt"])
            if "y_limits" in primary:
                ax.set_ylim(_y_limits(np.array([0.0]), explicit_limits=primary["y_limits"]))
            elif primary_values:
                ax.set_ylim(_y_limits(np.concatenate(primary_values), padding_fraction=0.08))

        secondary = panel_spec.get("secondary")
        if secondary:
            ax2 = ax.twinx()
            _apply_secondary_axis_style(ax2, tokens=tokens)
            secondary_values: list[np.ndarray] = []
            for series_spec in secondary["series"]:
                column = series_spec["column"]
                if column not in work.columns:
                    continue
                values = pd.to_numeric(work[column], errors="coerce")
                handle = ax2.plot(
                    work["datetime"],
                    values,
                    color=series_spec["color"],
                    linewidth=float(series_spec["linewidth_pt"]),
                    label=series_spec["label"],
                )[0]
                handles.append(handle)
                labels.append(series_spec["label"])
                secondary_values.append(values.to_numpy(dtype=float))
            ax2.set_ylabel(secondary["y_label"], fontsize=fonts["axis_label_size_pt"])
            if "y_limits" in secondary:
                ax2.set_ylim(_y_limits(np.array([0.0]), explicit_limits=secondary["y_limits"]))
            elif secondary_values:
                ax2.set_ylim(_y_limits(np.concatenate(secondary_values), padding_fraction=0.08))

        if handles:
            ax.legend(handles, labels, loc="upper left", fontsize=fonts["legend_size_pt"], ncol=min(5, len(labels)))
        _panel_label(ax, tokens=tokens, letter=_PANEL_LETTERS[idx])

    fig.suptitle(
        spec["meta"]["title"],
        x=0.5,
        y=0.985,
        fontsize=fonts["title_size_pt"] + 2,
        fontweight="bold",
    )
    _write_bundle_sidecars(
        spec_path=spec_path,
        spec=spec,
        tokens_path=tokens_path,
        file_paths=file_paths,
        data_frame=work,
        extra_metadata={"panel_count": len(spec["panel_order"])},
    )
    return _save_bundle_figure(fig=fig, spec=spec, tokens=tokens, file_paths=file_paths)


def render_allocation_compare_bundle(
    *,
    merged: pd.DataFrame,
    baseline_label: str,
    candidate_label: str,
    out_path: Path,
    spec_path: Path,
) -> FigureBundleArtifacts:
    plt, mdates = _require_matplotlib()
    spec, tokens, tokens_path, file_paths = _prepare_bundle(
        spec_path=spec_path,
        out_path=out_path,
        label_overrides={"baseline": baseline_label, "candidate": candidate_label},
    )
    fig, axes = plt.subplots(
        spec["layout"]["rows"],
        spec["layout"]["cols"],
        figsize=_figure_size(spec),
        dpi=int(spec["export"]["dpi"]),
        facecolor=tokens["figure"]["background"],
        constrained_layout=False,
    )
    fig.subplots_adjust(left=0.10, right=0.98, bottom=0.10, top=0.92, hspace=float(spec["layout"]["hspace"]))
    axes_vec = np.atleast_1d(axes).reshape(-1)
    fonts = tokens["fonts"]
    work = merged.copy()
    work["datetime"] = pd.to_datetime(work["datetime"])
    locator = mdates.AutoDateLocator(minticks=4, maxticks=10)

    for idx, panel_id in enumerate(spec["panel_order"]):
        ax = axes_vec[idx]
        panel_spec = spec["panels"][panel_id]
        show_xlabels = idx == len(spec["panel_order"]) - 1
        apply_axis_theme(ax, tokens=tokens, show_xlabels=show_xlabels)
        ax.set_title(panel_spec["title"], fontsize=fonts["title_size_pt"], loc="left", pad=6)
        ax.set_ylabel(panel_spec["y_label"], fontsize=fonts["axis_label_size_pt"])
        ax.xaxis.set_major_locator(locator)
        ax.xaxis.set_major_formatter(mdates.ConciseDateFormatter(locator))
        if show_xlabels:
            ax.set_xlabel(panel_spec["x_label"], fontsize=fonts["axis_label_size_pt"])
        ax.set_ylim(_y_limits(np.array([0.0]), explicit_limits=panel_spec.get("y_limits")))

        column = panel_spec["column"]
        for source_name, style in spec["styling"]["sources"].items():
            values = pd.to_numeric(work[f"{column}__{source_name}"], errors="coerce")
            ax.plot(
                work["datetime"],
                values,
                color=style["color"],
                linestyle=style["linestyle"],
                marker=style.get("marker"),
                linewidth=float(style["linewidth_pt"]),
                label=style["label"],
            )

        if idx == 0:
            ax.legend(loc="upper left", fontsize=fonts["legend_size_pt"])
        _panel_label(ax, tokens=tokens, letter=_PANEL_LETTERS[idx])

    fig.suptitle(
        spec["meta"]["title"],
        x=0.5,
        y=0.985,
        fontsize=fonts["title_size_pt"] + 2,
        fontweight="bold",
    )
    _write_bundle_sidecars(
        spec_path=spec_path,
        spec=spec,
        tokens_path=tokens_path,
        file_paths=file_paths,
        data_frame=work,
        extra_metadata={"panel_count": len(spec["panel_order"])},
    )
    return _save_bundle_figure(fig=fig, spec=spec, tokens=tokens, file_paths=file_paths)
