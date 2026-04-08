from __future__ import annotations

import io
import json
import re
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.datasets.contracts import (
    DatasetBasisContract,
    DatasetCapability,
    DatasetMetadataContract,
    DatasetObservationContract,
)
from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.datasets.registry import (
    DatasetRegistry,
)

REQUIRED_TRAITENV_FILES = (
    "source_inventory.csv",
    "source_summary.csv",
    "variable_dictionary.csv",
    "comparison_rules.csv",
    "integration_contract.json",
    "run_manifest.json",
    "workbook_index.csv",
    "comparison_daily.csv",
    "traitenv_design_workbook.xlsx",
)


@dataclass(frozen=True, slots=True)
class TraitenvInventoryBundle:
    bundle_path: Path
    bundle_kind: str
    source_inventory: pd.DataFrame
    source_summary: pd.DataFrame
    variable_dictionary: pd.DataFrame
    comparison_rules: pd.DataFrame
    integration_contract: dict[str, Any]
    run_manifest: dict[str, Any]
    workbook_index: pd.DataFrame
    comparison_daily: pd.DataFrame
    design_workbook_present: bool


def _read_csv_from_archive(archive: zipfile.ZipFile, member_name: str) -> pd.DataFrame:
    with archive.open(member_name) as handle:
        return pd.read_csv(handle)


def _read_json_from_archive(archive: zipfile.ZipFile, member_name: str) -> dict[str, Any]:
    with archive.open(member_name) as handle:
        return json.load(io.TextIOWrapper(handle, encoding="utf-8"))


def _resolve_archive_members(archive: zipfile.ZipFile) -> dict[str, str]:
    members: dict[str, str] = {}
    for member_name in archive.namelist():
        if member_name.endswith("/"):
            continue
        base_name = Path(member_name).name
        if base_name in REQUIRED_TRAITENV_FILES:
            members[base_name] = member_name
    return members


def _slugify(*parts: str) -> str:
    raw = "__".join(str(part).strip().lower() for part in parts if str(part).strip())
    return re.sub(r"[^a-z0-9]+", "_", raw).strip("_")


def _capability_for_candidate(dataset_family: str, observation_family: str) -> DatasetCapability:
    family = str(dataset_family).strip().lower()
    observation = str(observation_family).strip().lower()
    if observation == "yield" and family in {"school_trait_bundle", "public_rda", "public_ai_competition"}:
        return DatasetCapability.MEASURED_HARVEST
    if observation == "yield_environment" or ("yield" in observation and observation != "yield"):
        return DatasetCapability.HARVEST_PROXY
    return DatasetCapability.CONTEXT_ONLY


def _candidate_date_key(
    *,
    dataset_daily_rows: pd.DataFrame,
    observation_family: str,
    available_standard_names: set[str],
) -> str | None:
    if dataset_daily_rows.empty:
        return None
    if "environment" in observation_family and "observation_datetime" in available_standard_names:
        return "observation_datetime"
    if "observation_date" in available_standard_names:
        return "observation_date"
    return None


def load_traitenv_inventory(bundle_path: str | Path) -> TraitenvInventoryBundle:
    path = Path(bundle_path).expanduser().resolve()
    if not path.exists():
        raise FileNotFoundError(f"Could not find traitenv bundle at {path}.")
    if path.is_dir():
        missing = [name for name in REQUIRED_TRAITENV_FILES if not (path / name).exists()]
        if missing:
            raise FileNotFoundError(f"traitenv directory is missing required files: {missing}")
        return TraitenvInventoryBundle(
            bundle_path=path,
            bundle_kind="directory",
            source_inventory=pd.read_csv(path / "source_inventory.csv"),
            source_summary=pd.read_csv(path / "source_summary.csv"),
            variable_dictionary=pd.read_csv(path / "variable_dictionary.csv"),
            comparison_rules=pd.read_csv(path / "comparison_rules.csv"),
            integration_contract=json.loads((path / "integration_contract.json").read_text(encoding="utf-8")),
            run_manifest=json.loads((path / "run_manifest.json").read_text(encoding="utf-8")),
            workbook_index=pd.read_csv(path / "workbook_index.csv"),
            comparison_daily=pd.read_csv(path / "comparison_daily.csv"),
            design_workbook_present=True,
        )
    if path.suffix.lower() != ".zip":
        raise ValueError(f"traitenv bundle must be a directory or .zip, got {path}.")
    with zipfile.ZipFile(path) as archive:
        members = _resolve_archive_members(archive)
        missing = [name for name in REQUIRED_TRAITENV_FILES if name not in members]
        if missing:
            raise FileNotFoundError(f"traitenv archive is missing required files: {missing}")
        return TraitenvInventoryBundle(
            bundle_path=path,
            bundle_kind="zip",
            source_inventory=_read_csv_from_archive(archive, members["source_inventory.csv"]),
            source_summary=_read_csv_from_archive(archive, members["source_summary.csv"]),
            variable_dictionary=_read_csv_from_archive(archive, members["variable_dictionary.csv"]),
            comparison_rules=_read_csv_from_archive(archive, members["comparison_rules.csv"]),
            integration_contract=_read_json_from_archive(archive, members["integration_contract.json"]),
            run_manifest=_read_json_from_archive(archive, members["run_manifest.json"]),
            workbook_index=_read_csv_from_archive(archive, members["workbook_index.csv"]),
            comparison_daily=_read_csv_from_archive(archive, members["comparison_daily.csv"]),
            design_workbook_present=True,
        )


def build_traitenv_candidate_registry(bundle_path: TraitenvInventoryBundle | str | Path) -> DatasetRegistry:
    bundle = bundle_path if isinstance(bundle_path, TraitenvInventoryBundle) else load_traitenv_inventory(bundle_path)
    source_summary = bundle.source_summary.copy()
    source_inventory = bundle.source_inventory.copy()
    available_standard_names = {
        str(value).strip()
        for value in bundle.variable_dictionary.get("standard_name", pd.Series(dtype=object)).dropna().astype(str)
        if str(value).strip()
    }
    if source_summary.empty:
        raise ValueError("traitenv source_summary.csv did not contain any dataset rows.")
    datasets: list[DatasetMetadataContract] = []
    for row in source_summary.to_dict(orient="records"):
        dataset_family = str(row.get("dataset_family", "")).strip()
        observation_family = str(row.get("observation_family", "")).strip()
        if not dataset_family or not observation_family:
            continue
        subset = source_inventory.loc[
            source_inventory["dataset_family"].astype(str).eq(dataset_family)
            & source_inventory["observation_family"].astype(str).eq(observation_family)
        ].copy()
        capability = _capability_for_candidate(dataset_family, observation_family)
        source_refs = tuple(
            str(value)
            for value in subset.get("relative_path", pd.Series(dtype=object)).dropna().astype(str).head(25).tolist()
        )
        source_groups = sorted({str(value) for value in subset.get("source_group", pd.Series(dtype=object)).dropna()})
        grain_hints = sorted({str(value) for value in subset.get("grain_hint", pd.Series(dtype=object)).dropna()})
        rollup_hints = sorted(
            {str(value) for value in subset.get("comparison_rollup_hint", pd.Series(dtype=object)).dropna()}
        )
        metadata_join_hints = sorted(
            {str(value) for value in subset.get("metadata_join_hint", pd.Series(dtype=object)).dropna()}
        )
        preview_statuses = sorted({str(value) for value in subset.get("preview_status", pd.Series(dtype=object)).dropna()})
        comparison_daily_subset = bundle.comparison_daily.loc[
            bundle.comparison_daily.get("dataset_family", pd.Series(dtype=object)).astype(str).eq(dataset_family)
            & bundle.comparison_daily.get("observation_family", pd.Series(dtype=object)).astype(str).eq(observation_family)
        ].copy()
        daily_standard_names = sorted(
            {
                str(value)
                for value in comparison_daily_subset.get("standard_name", pd.Series(dtype=object)).dropna().astype(str)
                if str(value).strip()
            }
        )
        candidate_date_key = _candidate_date_key(
            dataset_daily_rows=comparison_daily_subset,
            observation_family=observation_family,
            available_standard_names=available_standard_names,
        )
        candidate_harvest_column = (
            "total_yield_weight_g"
            if observation_family == "yield" and "total_yield_weight_g" in daily_standard_names
            else None
        )
        relevant_rule_mask = (
            bundle.comparison_rules.get("scope", pd.Series(dtype=object))
            .astype(str)
            .str.contains(dataset_family, case=False, na=False)
            | bundle.comparison_rules.get("scope", pd.Series(dtype=object))
            .astype(str)
            .str.contains(observation_family, case=False, na=False)
            | bundle.comparison_rules.get("scope", pd.Series(dtype=object)).astype(str).str.contains("all", case=False, na=False)
        )
        relevant_rules = bundle.comparison_rules.loc[relevant_rule_mask].copy()
        candidate_id = f"{dataset_family}__{observation_family}".lower()
        datasets.append(
            DatasetMetadataContract(
                dataset_id=candidate_id,
                dataset_kind="traitenv_candidate",
                display_name=f"{dataset_family} / {observation_family}",
                dataset_family=dataset_family,
                observation_family=observation_family,
                capability=capability,
                source_refs=source_refs,
                cultivar="unknown",
                greenhouse="unknown",
                season="unknown",
                basis=DatasetBasisContract(reporting_basis="unknown", plants_per_m2=None),
                observation=DatasetObservationContract(
                    date_column=None,
                    measured_cumulative_column=None,
                    measured_semantics="cumulative_harvested_fruit_dry_weight_floor_area",
                    daily_increment_column=None,
                ),
                provenance_tags=tuple(source_groups + [dataset_family, observation_family]),
                notes={
                    "source_group_candidates": source_groups,
                    "grain_hints": grain_hints,
                    "comparison_rollup_hints": rollup_hints,
                    "metadata_join_hints": metadata_join_hints,
                    "preview_statuses": preview_statuses,
                    "traitenv_bundle_kind": bundle.bundle_kind,
                    "traitenv_bundle_ref": bundle.bundle_path.name,
                    "design_workbook_present": bundle.design_workbook_present,
                    "n_files": int(row.get("n_files", 0) or 0),
                    "candidate_date_key": candidate_date_key,
                    "candidate_harvest_column": candidate_harvest_column,
                    "candidate_harvest_requires_cumulative_construction": candidate_harvest_column is not None,
                    "candidate_harvest_includes_fallen_fruit": observation_family == "yield",
                    "comparison_daily_standard_names": daily_standard_names,
                    "comparison_rule_ids": [
                        str(value)
                        for value in relevant_rules.get("rule_id", pd.Series(dtype=object)).dropna().astype(str).tolist()
                    ],
                    "integration_fact_tables": [
                        str(fact.get("name"))
                        for fact in bundle.integration_contract.get("fact_tables", [])
                        if isinstance(fact, dict) and str(fact.get("name", "")).strip()
                    ],
                    "special_rules": [
                        str(value)
                        for value in bundle.integration_contract.get("special_rules", [])
                        if str(value).strip()
                    ],
                },
            )
        )
    datasets_tuple = tuple(sorted(datasets, key=lambda dataset: (dataset.dataset_family, dataset.observation_family)))
    return DatasetRegistry(datasets=datasets_tuple, default_dataset_ids=())


__all__ = ["TraitenvInventoryBundle", "build_traitenv_candidate_registry", "load_traitenv_inventory"]
