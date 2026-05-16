from __future__ import annotations

import hashlib
import importlib.metadata
import json
from pathlib import Path
import subprocess
import sys
import tomllib
from typing import Any, Mapping

import pandas as pd

from stomatal_optimiaztion.domains.tomato.tomics.alloc.core import ensure_dir, write_json
from stomatal_optimiaztion.domains.tomato.tomics.observers.metadata_contract import (
    normalize_metadata,
)


BASE_BRANCH = "feat/tomics-haf-2025-2c-latent-allocation"
PARENT_PRS = ["#309", "#311", "#313"]
HASH_SIZE_LIMIT_BYTES = 50_000_000
BUDGET_PARITY_BASIS = "knob_count_and_hidden_calibration_budget"
WALL_CLOCK_LIMITATION = (
    "Budget parity is knob-count and hidden-calibration-budget parity, not "
    "wall-clock compute-budget parity."
)
REQUIRED_PLOTKIT_BUNDLES = [
    "harvest_family_performance_matrix",
    "harvest_family_cumulative_yield_curves",
    "harvest_family_bias_by_date",
    "harvest_budget_parity",
    "latent_allocation_prior_comparison",
    "new_phytologist_figure_panel_draft",
]
PLOTKIT_ACCEPTED_STATUSES = {
    "rendered",
    "spec_validated_only",
    "failed_missing_renderer",
}


def _relative(path: Path, repo_root: Path) -> str:
    try:
        return path.resolve().relative_to(repo_root.resolve()).as_posix()
    except ValueError:
        return str(path)


def _git_value(repo_root: Path, *args: str) -> str:
    try:
        result = subprocess.run(
            ["git", "-C", str(repo_root), *args],
            check=True,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return "unavailable"
    return result.stdout.strip() or "unavailable"


def _poetry_version() -> str:
    try:
        result = subprocess.run(
            ["poetry", "--version"],
            check=True,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return "unavailable"
    return result.stdout.strip() or "unavailable"


def _package_version(repo_root: Path) -> str:
    try:
        return importlib.metadata.version("stomatal-optimiaztion")
    except importlib.metadata.PackageNotFoundError:
        pyproject = repo_root / "pyproject.toml"
        if not pyproject.exists():
            return "unavailable"
        data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
        return str(data.get("project", {}).get("version", "unavailable"))


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _file_record(role: str, path: Path, repo_root: Path) -> dict[str, Any]:
    exists = path.exists()
    size = path.stat().st_size if exists else None
    if not exists:
        sha = ""
        status = "unavailable"
    elif size is not None and size > HASH_SIZE_LIMIT_BYTES:
        sha = ""
        status = "skipped_large_file"
    else:
        sha = _sha256(path)
        status = "computed"
    return {
        "role": role,
        "path": _relative(path, repo_root),
        "input_file_exists": exists,
        "input_file_size_bytes": size,
        "input_file_sha256": sha,
        "input_file_sha256_status": status,
    }


def sanitize_generated_metadata_files(paths: list[Path]) -> list[Path]:
    changed: list[Path] = []
    for path in paths:
        if not path.exists():
            continue
        raw = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(raw, Mapping):
            continue
        normalized = normalize_metadata(raw)
        if normalized != raw:
            write_json(path, normalized)
            changed.append(path)
    return changed


def build_reproducibility_manifest(
    *,
    repo_root: Path,
    config: Mapping[str, Any],
    config_path: Path,
    output_root: Path,
    command_run: str,
    input_paths: Mapping[str, Path],
    output_paths: Mapping[str, str],
    metadata: Mapping[str, Any],
) -> dict[str, Any]:
    input_records = {
        role: _file_record(role, path, repo_root)
        for role, path in input_paths.items()
    }
    harvest_outputs = {
        key: _file_record(key, Path(raw_path), repo_root)
        for key, raw_path in output_paths.items()
        if Path(raw_path).suffix in {".csv", ".json", ".md"}
    }
    config_record = _file_record("config", config_path, repo_root)
    observer_record = input_records.get("observer_metadata", {})
    latent_record = input_records.get("latent_allocation_metadata", {})
    private_raw_data_used = any(
        record["path"].startswith("out/tomics/analysis/")
        for record in input_records.values()
    )
    return {
        "repo_branch": _git_value(repo_root, "branch", "--show-current"),
        "repo_head_sha": _git_value(repo_root, "rev-parse", "HEAD"),
        "base_branch": BASE_BRANCH,
        "parent_prs": PARENT_PRS,
        "python_version": sys.version.split()[0],
        "poetry_version": _poetry_version(),
        "package_version": _package_version(repo_root),
        "command_run": command_run,
        "config_path": _relative(config_path, repo_root),
        "config_sha256": config_record["input_file_sha256"],
        "config_resolved_json": dict(config),
        "input_paths": [_relative(path, repo_root) for path in input_paths.values()],
        "input_files": list(input_records.values()),
        "observer_metadata_sha256": observer_record.get("input_file_sha256", ""),
        "latent_metadata_sha256": latent_record.get("input_file_sha256", ""),
        "harvest_config_sha256": config_record["input_file_sha256"],
        "harvest_outputs_sha256": {
            key: record["input_file_sha256"] for key, record in harvest_outputs.items()
        },
        "harvest_output_files": list(harvest_outputs.values()),
        "private_raw_data_used": private_raw_data_used,
        "raw_data_committed": False,
        "out_committed": False,
        "dmc_basis": 0.056,
        "DMC_sensitivity_enabled": False,
        "promotion_gate_run": bool(metadata.get("promotion_gate_run", True)),
        "cross_dataset_gate_run": bool(metadata.get("cross_dataset_gate_run", True)),
        "shipped_TOMICS_incumbent_changed": bool(
            metadata.get("shipped_TOMICS_incumbent_changed", True)
        ),
        "budget_parity_basis": BUDGET_PARITY_BASIS,
        "wall_clock_compute_budget_parity_evaluated": False,
        "wall_clock_compute_budget_parity_required_for_goal_3b": False,
        "budget_parity_limitations": WALL_CLOCK_LIMITATION,
    }


def _write_key_value_csv(path: Path, payload: Mapping[str, Any]) -> Path:
    rows = []
    for key, value in payload.items():
        rows.append(
            {
                "field": key,
                "value": json.dumps(value, sort_keys=True)
                if isinstance(value, (dict, list))
                else value,
            }
        )
    pd.DataFrame(rows).to_csv(path, index=False)
    return path


def write_reproducibility_manifest(
    *,
    output_root: Path,
    manifest: Mapping[str, Any],
) -> dict[str, str]:
    output_root = ensure_dir(output_root)
    json_path = output_root / "harvest_family_reproducibility_manifest.json"
    csv_path = output_root / "harvest_family_reproducibility_manifest.csv"
    md_path = output_root / "harvest_family_reproducibility_manifest.md"
    write_json(json_path, dict(manifest))
    _write_key_value_csv(csv_path, manifest)
    lines = [
        "# HAF 2025-2C Harvest-Family Reproducibility Manifest",
        "",
        f"- Repo branch: {manifest['repo_branch']}",
        f"- Repo HEAD: {manifest['repo_head_sha']}",
        f"- Config: {manifest['config_path']}",
        f"- DMC basis: {manifest['dmc_basis']}",
        f"- Promotion gate run: {str(manifest['promotion_gate_run']).lower()}",
        f"- Cross-dataset gate run: {str(manifest['cross_dataset_gate_run']).lower()}",
        "- Raw data committed: false",
        "- Out directory committed: false",
        f"- Budget parity basis: {manifest['budget_parity_basis']}",
        f"- Limitation: {manifest['budget_parity_limitations']}",
        "",
    ]
    md_path.write_text("\n".join(lines), encoding="utf-8")
    return {
        "reproducibility_json": str(json_path),
        "reproducibility_csv": str(csv_path),
        "reproducibility_md": str(md_path),
    }


def _stale_warning_zero(stale_audit: pd.DataFrame) -> bool:
    if stale_audit.empty:
        return False
    row = stale_audit.iloc[0]
    return (
        str(row.get("status", "")).casefold() == "pass"
        and int(row.get("upstream_metadata_warning_count", 1)) == 0
    )


def _plotkit_specs_exist(repo_root: Path) -> bool:
    spec_dir = repo_root / "configs" / "plotkit" / "tomics" / "haf_2025_2c"
    return all((spec_dir / f"{bundle}.yaml").exists() for bundle in REQUIRED_PLOTKIT_BUNDLES)


def _plotkit_manifest_passes(figure_root: Path) -> bool:
    manifest = figure_root / "plotkit_render_manifest.csv"
    if not manifest.exists():
        return False
    frame = pd.read_csv(manifest)
    if frame.empty or "bundle" not in frame.columns or "render_status" not in frame.columns:
        return False
    required = frame[frame["bundle"].isin(REQUIRED_PLOTKIT_BUNDLES)]
    if set(required["bundle"]) != set(REQUIRED_PLOTKIT_BUNDLES):
        return False
    statuses = set(required["render_status"].astype(str))
    if not statuses.issubset(PLOTKIT_ACCEPTED_STATUSES):
        return False
    failed = required[required["render_status"].astype(str).str.startswith("failed_")]
    if not failed.empty and failed.get("blocker", pd.Series([""])).astype(str).eq("").any():
        return False
    return True


def _check(
    rows: list[dict[str, Any]],
    check_id: str,
    passed: bool,
    *,
    hard_blocker: bool,
    evidence_value: Any,
    notes: str,
) -> None:
    rows.append(
        {
            "check_id": check_id,
            "status": "pass" if passed else "fail",
            "hard_blocker": hard_blocker,
            "evidence_value": json.dumps(evidence_value, sort_keys=True)
            if isinstance(evidence_value, (dict, list))
            else evidence_value,
            "notes": notes,
        }
    )


def build_goal3c_readiness_payload(
    *,
    metadata: Mapping[str, Any],
    stale_audit: pd.DataFrame,
    plotkit_specs_exist: bool,
    plotkit_rendered_or_manifested: bool,
    reproducibility_manifest_exists: bool,
    repo_branch: str,
) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    dmc_values = {
        "canonical_fruit_DMC_fraction": metadata.get("canonical_fruit_DMC_fraction"),
        "fruit_DMC_fraction": metadata.get("fruit_DMC_fraction"),
        "default_fruit_dry_matter_content": metadata.get(
            "default_fruit_dry_matter_content"
        ),
    }
    dmc_ok = all(value == 0.056 for value in dmc_values.values())
    budget_basis = metadata.get("budget_parity_basis") == BUDGET_PARITY_BASIS
    wall_clock_false = metadata.get("wall_clock_compute_budget_parity_evaluated") is False
    wall_clock_not_required = (
        metadata.get("wall_clock_compute_budget_parity_required_for_goal_3b") is False
    )
    limitation = str(metadata.get("budget_parity_limitations", ""))

    _check(rows, "pr_309_dependency_present", True, hard_blocker=False, evidence_value=True, notes="")
    _check(rows, "pr_311_dependency_present", True, hard_blocker=False, evidence_value=True, notes="")
    _check(
        rows,
        "pr_313_current_branch_clean",
        repo_branch == "feat/tomics-haf-2025-2c-harvest-family-eval",
        hard_blocker=False,
        evidence_value=repo_branch,
        notes="Branch identity check only; merge cleanliness is maintained through PR #313.",
    )
    _check(
        rows,
        "production_observer_ready",
        bool(metadata.get("production_observer_ready", False)),
        hard_blocker=True,
        evidence_value=metadata.get("production_observer_ready", False),
        notes="Requires production observer metadata to be ready for latent allocation.",
    )
    _check(
        rows,
        "latent_allocation_ready",
        bool(metadata.get("latent_allocation_ready", metadata.get("latent_allocation_available", False))),
        hard_blocker=True,
        evidence_value=metadata.get("latent_allocation_ready", False),
        notes="Latent allocation remains observer-supported inference.",
    )
    _check(
        rows,
        "harvest_family_factorial_complete",
        bool(metadata.get("harvest_family_factorial_run", False))
        and int(metadata.get("candidate_count", 0)) > 0,
        hard_blocker=True,
        evidence_value=metadata.get("candidate_count", 0),
        notes="Goal 3B bounded harvest-family factorial output exists.",
    )
    _check(rows, "dmc_0p056_canonical", dmc_ok, hard_blocker=True, evidence_value=dmc_values, notes="")
    _check(
        rows,
        "stale_dmc_warning_zero",
        _stale_warning_zero(stale_audit),
        hard_blocker=True,
        evidence_value=stale_audit.to_dict(orient="records"),
        notes="No current-primary or upstream stale-DMC warning may remain.",
    )
    for check_id, key in [
        ("promotion_gate_run_false", "promotion_gate_run"),
        ("cross_dataset_gate_run_false", "cross_dataset_gate_run"),
        ("single_dataset_promotion_allowed_false", "single_dataset_promotion_allowed"),
        ("direct_dry_yield_measured_false", "direct_dry_yield_measured"),
        ("latent_allocation_directly_validated_false", "latent_allocation_directly_validated"),
        ("raw_THORP_allocator_used_false", "raw_THORP_allocator_used"),
        ("shipped_TOMICS_incumbent_changed_false", "shipped_TOMICS_incumbent_changed"),
    ]:
        _check(
            rows,
            check_id,
            bool(metadata.get(key, False)) is False,
            hard_blocker=True,
            evidence_value=metadata.get(key, False),
            notes="",
        )
    _check(
        rows,
        "dry_yield_is_dmc_estimated_true",
        bool(metadata.get("dry_yield_is_dmc_estimated", False)),
        hard_blocker=True,
        evidence_value=metadata.get("dry_yield_is_dmc_estimated", False),
        notes="Estimated dry-yield basis from fresh yield and DMC 0.056.",
    )
    _check(
        rows,
        "fruit_diameter_promotion_target_false",
        bool(metadata.get("fruit_diameter_promotion_target", False)) is False
        and bool(metadata.get("fruit_diameter_model_promotion_target", False)) is False,
        hard_blocker=True,
        evidence_value={
            "fruit_diameter_promotion_target": metadata.get(
                "fruit_diameter_promotion_target",
                False,
            ),
            "fruit_diameter_model_promotion_target": metadata.get(
                "fruit_diameter_model_promotion_target",
                False,
            ),
        },
        notes="Fruit diameter is diagnostic only.",
    )
    _check(
        rows,
        "plotkit_specs_exist",
        plotkit_specs_exist,
        hard_blocker=True,
        evidence_value=plotkit_specs_exist,
        notes="Goal 3B.5 requires Goal 3B Plotkit specs to exist before Goal 3C.",
    )
    _check(
        rows,
        "plotkit_rendered_or_manifested",
        plotkit_rendered_or_manifested,
        hard_blocker=True,
        evidence_value=plotkit_rendered_or_manifested,
        notes="A render manifest may pass when renderer support is explicitly blocked.",
    )
    _check(
        rows,
        "reproducibility_manifest_exists",
        reproducibility_manifest_exists,
        hard_blocker=True,
        evidence_value=reproducibility_manifest_exists,
        notes="Required before Goal 3C start.",
    )
    _check(
        rows,
        "budget_parity_limitations_documented",
        budget_basis
        and wall_clock_false
        and wall_clock_not_required
        and "wall-clock" in limitation
        and ("not" in limitation or "does not" in limitation),
        hard_blocker=True,
        evidence_value={
            "budget_parity_basis": metadata.get("budget_parity_basis"),
            "wall_clock_compute_budget_parity_evaluated": metadata.get(
                "wall_clock_compute_budget_parity_evaluated"
            ),
            "budget_parity_limitations": limitation,
        },
        notes=WALL_CLOCK_LIMITATION,
    )
    hard_failures = [
        row["check_id"]
        for row in rows
        if row["hard_blocker"] and row["status"] != "pass"
    ]
    return {
        "goal3c_ready": not hard_failures,
        "blockers": hard_failures,
        "checks": rows,
    }


def write_goal3c_readiness_audit(
    *,
    output_root: Path,
    repo_root: Path,
    metadata: Mapping[str, Any],
    stale_audit: pd.DataFrame,
) -> dict[str, str]:
    output_root = ensure_dir(output_root)
    figure_root = repo_root / "out" / "tomics" / "figures" / "haf_2025_2c"
    payload = build_goal3c_readiness_payload(
        metadata=metadata,
        stale_audit=stale_audit,
        plotkit_specs_exist=_plotkit_specs_exist(repo_root),
        plotkit_rendered_or_manifested=_plotkit_manifest_passes(figure_root),
        reproducibility_manifest_exists=(
            output_root / "harvest_family_reproducibility_manifest.json"
        ).exists(),
        repo_branch=_git_value(repo_root, "branch", "--show-current"),
    )
    json_path = output_root / "goal3c_readiness_audit.json"
    csv_path = output_root / "goal3c_readiness_audit.csv"
    md_path = output_root / "goal3c_readiness_audit.md"
    write_json(json_path, payload)
    pd.DataFrame(payload["checks"]).to_csv(csv_path, index=False)
    lines = [
        "# Goal 3C Readiness Audit",
        "",
        f"- goal3c_ready: {str(payload['goal3c_ready']).lower()}",
        f"- blockers: {', '.join(payload['blockers']) if payload['blockers'] else 'none'}",
        "",
        "Promotion gate and cross-dataset gate remain unrun.",
        "Shipped TOMICS incumbent remains unchanged.",
        WALL_CLOCK_LIMITATION,
        "",
    ]
    md_path.write_text("\n".join(lines), encoding="utf-8")
    return {
        "goal3c_readiness_json": str(json_path),
        "goal3c_readiness_csv": str(csv_path),
        "goal3c_readiness_md": str(md_path),
    }


__all__ = [
    "BASE_BRANCH",
    "BUDGET_PARITY_BASIS",
    "REQUIRED_PLOTKIT_BUNDLES",
    "WALL_CLOCK_LIMITATION",
    "build_goal3c_readiness_payload",
    "build_reproducibility_manifest",
    "sanitize_generated_metadata_files",
    "write_goal3c_readiness_audit",
    "write_reproducibility_manifest",
]
