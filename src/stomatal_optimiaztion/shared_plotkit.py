from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import yaml


@dataclass(frozen=True)
class FigureBundleArtifacts:
    output_dir: Path
    png_path: Path
    data_csv_path: Path | None = None
    python_csv_path: Path | None = None
    legacy_csv_path: Path | None = None
    diff_csv_path: Path | None = None
    spec_copy_path: Path | None = None
    resolved_spec_path: Path | None = None
    tokens_copy_path: Path | None = None
    metadata_path: Path | None = None

    def to_summary(self) -> dict[str, Any]:
        summary = {
            "output_dir": str(self.output_dir),
            "png": str(self.png_path),
        }
        optional_paths = {
            "data_csv": self.data_csv_path,
            "python_csv": self.python_csv_path,
            "legacy_csv": self.legacy_csv_path,
            "diff_csv": self.diff_csv_path,
            "spec_copy": self.spec_copy_path,
            "resolved_spec": self.resolved_spec_path,
            "tokens_copy": self.tokens_copy_path,
            "metadata": self.metadata_path,
        }
        for key, path in optional_paths.items():
            if path is not None:
                summary[key] = str(path)
        return summary


def load_yaml(path: Path) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def apply_axis_theme(ax: Any, *, tokens: dict[str, Any], show_xlabels: bool) -> None:
    axes_tokens = tokens["axes"]
    ax.set_facecolor(tokens["figure"]["background"])
    ax.grid(
        axis=axes_tokens.get("grid_major", "y"),
        color=axes_tokens["grid_color"],
        linewidth=axes_tokens["grid_width_pt"],
        alpha=axes_tokens["grid_alpha"],
    )
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


def resolve_figure_paths(output_dir: Path, figure_id: str) -> dict[str, Path]:
    return {
        "data_csv": output_dir / f"{figure_id}_data.csv",
        "spec_copy": output_dir / f"{figure_id}_spec.yaml",
        "resolved_spec": output_dir / f"{figure_id}_resolved_spec.yaml",
        "tokens_copy": output_dir / f"{figure_id}_tokens.yaml",
        "metadata": output_dir / f"{figure_id}_metadata.json",
        "png": output_dir / f"{figure_id}.png",
    }


def frame_digest(frame: pd.DataFrame, *, float_decimals: int = 10) -> str:
    normalized = frame.copy()
    for column in normalized.columns:
        if pd.api.types.is_numeric_dtype(normalized[column]):
            normalized[column] = np.round(normalized[column].astype(float), float_decimals)
        else:
            normalized[column] = normalized[column].astype(str).fillna("")
    csv_blob = normalized.sort_values(list(normalized.columns)).to_csv(
        index=False,
        float_format=f"%.{float_decimals}f",
    )
    return sha256(csv_blob.encode("utf-8")).hexdigest()
