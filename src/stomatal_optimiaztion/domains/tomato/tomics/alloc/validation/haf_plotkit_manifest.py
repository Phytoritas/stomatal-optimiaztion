from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd
import yaml

from stomatal_optimiaztion.domains.tomato.tomics.alloc.core import ensure_dir
from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.haf_pre_gate_artifacts import (
    REQUIRED_PLOTKIT_BUNDLES,
)


OPTIONAL_OBSERVER_BUNDLES = [
    "radiation_photoperiod",
    "radiation_daynight_et_ratio",
    "rootzone_rzi_apparent_conductance",
    "fruit_diameter_raw_qc",
    "fruit_diameter_radiation_phase_expansion",
    "leaf_temp_pair",
    "loadcell_leaf_fruit_bridge",
    "dataset3_growth_phenology",
]
FRAME_ROLE_FILES = {
    "harvest_family_rankings": "harvest_family_rankings.csv",
    "harvest_family_cumulative_overlay": "harvest_family_cumulative_overlay.csv",
    "harvest_family_budget_parity": "harvest_family_budget_parity.csv",
    "harvest_family_metrics_pooled": "harvest_family_metrics_pooled.csv",
    "harvest_family_daily_overlay": "harvest_family_daily_overlay.csv",
}


def _load_spec(path: Path) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def _token_path(spec_path: Path, spec: dict[str, Any]) -> Path:
    tokens = spec.get("theme", {}).get("tokens", "")
    return (spec_path.parent / str(tokens)).resolve() if tokens else Path()


def _frame_roles(spec: dict[str, Any]) -> list[str]:
    data = spec.get("data", {})
    if "frame_role" in data:
        return [str(data["frame_role"])]
    if "frame_roles" in data and isinstance(data["frame_roles"], list):
        return [str(role) for role in data["frame_roles"]]
    return []


def _status_for_spec(
    *,
    spec: dict[str, Any],
    input_paths: list[Path],
) -> tuple[str, str]:
    missing_data = [str(path) for path in input_paths if not path.exists()]
    if missing_data:
        return "failed_missing_data", "missing input CSV: " + ";".join(missing_data)
    support_level = str(spec.get("meta", {}).get("support_level", ""))
    if support_level == "spec_scaffold":
        return (
            "spec_validated_only",
            "spec_scaffold_missing_renderer_layout_panels_styling",
        )
    return "failed_missing_renderer", f"unsupported HAF Plotkit kind: {spec.get('kind', '')}"


def build_haf_plotkit_render_manifest(
    *,
    spec_dir: Path,
    input_root: Path,
    output_root: Path,
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    bundles = list(REQUIRED_PLOTKIT_BUNDLES)
    bundles.extend(
        bundle for bundle in OPTIONAL_OBSERVER_BUNDLES if (spec_dir / f"{bundle}.yaml").exists()
    )
    for bundle in bundles:
        spec_path = spec_dir / f"{bundle}.yaml"
        if not spec_path.exists():
            rows.append(
                {
                    "bundle": bundle,
                    "figure_id": "",
                    "kind": "",
                    "support_level": "",
                    "spec_path": str(spec_path),
                    "spec_exists": False,
                    "tokens_path": "",
                    "tokens_exists": False,
                    "input_csvs": "",
                    "input_data_exists": False,
                    "intended_png": str(output_root / f"{bundle}.png"),
                    "intended_data_csv": str(output_root / f"{bundle}_data.csv"),
                    "intended_spec_copy": str(output_root / f"{bundle}_spec.yaml"),
                    "intended_resolved_spec": str(output_root / f"{bundle}_resolved_spec.yaml"),
                    "intended_tokens_copy": str(output_root / f"{bundle}_tokens.yaml"),
                    "intended_metadata": str(output_root / f"{bundle}_metadata.json"),
                    "render_status": "failed_missing_data",
                    "blocker": "missing Plotkit spec",
                }
            )
            continue
        spec = _load_spec(spec_path)
        roles = _frame_roles(spec)
        input_paths = [
            input_root / FRAME_ROLE_FILES[role]
            for role in roles
            if role in FRAME_ROLE_FILES
        ]
        tokens_path = _token_path(spec_path, spec)
        status, blocker = _status_for_spec(spec=spec, input_paths=input_paths)
        rows.append(
            {
                "bundle": bundle,
                "figure_id": spec.get("meta", {}).get("id", ""),
                "kind": spec.get("kind", ""),
                "support_level": spec.get("meta", {}).get("support_level", ""),
                "spec_path": str(spec_path),
                "spec_exists": True,
                "tokens_path": str(tokens_path) if tokens_path != Path() else "",
                "tokens_exists": bool(tokens_path != Path() and tokens_path.exists()),
                "input_csvs": ";".join(str(path) for path in input_paths),
                "input_data_exists": all(path.exists() for path in input_paths),
                "intended_png": str(output_root / f"{bundle}.png"),
                "intended_data_csv": str(output_root / f"{bundle}_data.csv"),
                "intended_spec_copy": str(output_root / f"{bundle}_spec.yaml"),
                "intended_resolved_spec": str(output_root / f"{bundle}_resolved_spec.yaml"),
                "intended_tokens_copy": str(output_root / f"{bundle}_tokens.yaml"),
                "intended_metadata": str(output_root / f"{bundle}_metadata.json"),
                "render_status": status,
                "blocker": blocker,
            }
        )
    return pd.DataFrame(rows)


def write_haf_plotkit_render_manifest(
    *,
    spec_dir: Path,
    input_root: Path,
    output_root: Path,
) -> dict[str, str]:
    output_root = ensure_dir(output_root)
    manifest = build_haf_plotkit_render_manifest(
        spec_dir=spec_dir,
        input_root=input_root,
        output_root=output_root,
    )
    csv_path = output_root / "plotkit_render_manifest.csv"
    md_path = output_root / "plotkit_render_manifest.md"
    manifest.to_csv(csv_path, index=False)
    rendered = int(manifest["render_status"].eq("rendered").sum()) if not manifest.empty else 0
    validated = (
        int(manifest["render_status"].eq("spec_validated_only").sum())
        if not manifest.empty
        else 0
    )
    failed = (
        int(manifest["render_status"].astype(str).str.startswith("failed_").sum())
        if not manifest.empty
        else 0
    )
    lines = [
        "# HAF 2025-2C Plotkit Render Manifest",
        "",
        f"- rendered: {rendered}",
        f"- spec_validated_only: {validated}",
        f"- failed: {failed}",
        "",
        "No fake PNGs are written by this manifest-only runner.",
        "Specs with `spec_scaffold` support need a future HAF renderer before PNG export.",
        "",
    ]
    md_path.write_text("\n".join(lines), encoding="utf-8")
    return {"plotkit_render_manifest_csv": str(csv_path), "plotkit_render_manifest_md": str(md_path)}


__all__ = [
    "FRAME_ROLE_FILES",
    "OPTIONAL_OBSERVER_BUNDLES",
    "build_haf_plotkit_render_manifest",
    "write_haf_plotkit_render_manifest",
]
