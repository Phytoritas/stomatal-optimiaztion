from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import yaml

from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.knu_data import (
    KnuValidationData,
    PLANTS_PER_M2,
)


@dataclass(frozen=True, slots=True)
class KnuDataContractPaths:
    forcing_path: Path
    yield_path: Path
    forcing_source_kind: str
    yield_source_kind: str
    reporting_basis: str
    plants_per_m2: float
    parser_assumptions: dict[str, Any]
    private_data_root: str | None = None
    contract_path: Path | None = None


def _as_dict(raw: object) -> dict[str, Any]:
    if isinstance(raw, dict):
        return {str(key): value for key, value in raw.items()}
    return {}


def _resolve_existing_path(path: str | Path, *, repo_root: Path, config_path: Path | None = None) -> Path:
    candidate = Path(path)
    if candidate.is_absolute():
        return candidate

    probes: list[Path] = []
    if config_path is not None:
        probes.append((config_path.parent / candidate).resolve())
    probes.append((repo_root / candidate).resolve())
    probes.append((Path.cwd() / candidate).resolve())
    for probe in probes:
        if probe.exists():
            return probe
    return probes[0]


def _load_contract_template(path: Path | None) -> dict[str, Any]:
    if path is None or not path.exists():
        return {}
    loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    return _as_dict(loaded)


def _resolve_private_root(contract: dict[str, Any]) -> tuple[str | None, str | None]:
    env_name = str(contract.get("private_data_root_env", "PHYTORITAS_PRIVATE_DATA_ROOT"))
    env_root = os.getenv(env_name)
    if env_root:
        return env_root, env_name
    configured = contract.get("private_data_root")
    if configured:
        return str(configured), None
    return None, env_name


def _resolve_source_path(
    *,
    repo_candidate: Path,
    private_root: str | None,
    configured_relative_path: str | None,
) -> tuple[Path, str]:
    if repo_candidate.exists():
        return repo_candidate, "repo_local"

    if private_root:
        root = Path(private_root).expanduser().resolve()
        relative_candidate = root / configured_relative_path if configured_relative_path else root / repo_candidate.name
        if relative_candidate.exists():
            return relative_candidate, "private_root"
        basename_candidate = root / repo_candidate.name
        if basename_candidate.exists():
            return basename_candidate, "private_root"

    return repo_candidate, "missing"


def resolve_knu_data_contract(
    *,
    validation_cfg: dict[str, Any],
    repo_root: Path,
    config_path: Path | None = None,
) -> KnuDataContractPaths:
    contract_path_raw = validation_cfg.get("private_data_contract_path")
    contract_path = (
        _resolve_existing_path(str(contract_path_raw), repo_root=repo_root, config_path=config_path)
        if contract_path_raw
        else None
    )
    contract = _load_contract_template(contract_path)
    private_root, env_name = _resolve_private_root(contract)

    forcing_raw = validation_cfg.get("forcing_csv_path", "data/forcing/KNU_Tomato_Env.CSV")
    yield_raw = validation_cfg.get("yield_xlsx_path", "data/forcing/tomato_validation_data_yield_260222.xlsx")
    forcing_repo_candidate = _resolve_existing_path(str(forcing_raw), repo_root=repo_root, config_path=config_path)
    yield_repo_candidate = _resolve_existing_path(str(yield_raw), repo_root=repo_root, config_path=config_path)

    forcing_path, forcing_source_kind = _resolve_source_path(
        repo_candidate=forcing_repo_candidate,
        private_root=private_root,
        configured_relative_path=str(contract.get("forcing_relative_path", forcing_repo_candidate.name)),
    )
    yield_path, yield_source_kind = _resolve_source_path(
        repo_candidate=yield_repo_candidate,
        private_root=private_root,
        configured_relative_path=str(contract.get("yield_relative_path", yield_repo_candidate.name)),
    )
    if forcing_source_kind == "missing":
        raise FileNotFoundError(
            f"Could not resolve KNU forcing CSV. Tried repo-local path {forcing_repo_candidate}"
            + (f" and private root {private_root!r}" if private_root else f"; env {env_name!r} was not configured")
        )
    if yield_source_kind == "missing":
        raise FileNotFoundError(
            f"Could not resolve KNU yield table. Tried repo-local path {yield_repo_candidate}"
            + (f" and private root {private_root!r}" if private_root else f"; env {env_name!r} was not configured")
        )

    parser_assumptions = {
        "forcing_parser": "csv_datetime_first_class",
        "yield_parser": yield_path.suffix.lower(),
        "units_policy": "preserve_source_declared_units",
        "datetime_policy": "naive_local_greenhouse_timestamps",
        "observation_semantics": "cumulative_harvested_fruit_dry_weight_floor_area",
        **_as_dict(contract.get("parser_assumptions")),
    }
    return KnuDataContractPaths(
        forcing_path=forcing_path,
        yield_path=yield_path,
        forcing_source_kind=forcing_source_kind,
        yield_source_kind=yield_source_kind,
        reporting_basis=str(contract.get("reporting_basis", "floor_area_g_m2")),
        plants_per_m2=float(contract.get("plants_per_m2", PLANTS_PER_M2)),
        parser_assumptions=parser_assumptions,
        private_data_root=private_root,
        contract_path=contract_path,
    )


def write_data_contract_manifest(
    *,
    output_root: Path,
    contract: KnuDataContractPaths,
    data: KnuValidationData,
) -> Path:
    output_root.mkdir(parents=True, exist_ok=True)
    manifest_path = output_root / "data_contract_manifest.json"
    payload = {
        "forcing_source_path": str(contract.forcing_path.resolve()),
        "yield_source_path": str(contract.yield_path.resolve()),
        "forcing_source_kind": contract.forcing_source_kind,
        "yield_source_kind": contract.yield_source_kind,
        "private_data_root": contract.private_data_root,
        "contract_path": str(contract.contract_path.resolve()) if contract.contract_path is not None else None,
        "reporting_basis": contract.reporting_basis,
        "plants_per_m2": contract.plants_per_m2,
        "observation_columns": {
            "measured": data.measured_column,
            "estimated": data.estimated_column,
        },
        "observation_unit_label": data.observation_unit_label,
        "time_coverage": {
            "forcing_start": data.forcing_summary["start"],
            "forcing_end": data.forcing_summary["end"],
            "yield_start": data.yield_summary["start"],
            "yield_end": data.yield_summary["end"],
        },
        "parser_assumptions": contract.parser_assumptions,
    }
    manifest_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return manifest_path


def contract_payload(contract: KnuDataContractPaths) -> dict[str, Any]:
    payload = asdict(contract)
    payload["forcing_path"] = str(contract.forcing_path)
    payload["yield_path"] = str(contract.yield_path)
    payload["contract_path"] = str(contract.contract_path) if contract.contract_path is not None else None
    return payload


__all__ = [
    "KnuDataContractPaths",
    "contract_payload",
    "resolve_knu_data_contract",
    "write_data_contract_manifest",
]
