from __future__ import annotations

import importlib
from pathlib import Path

import pytest
from stomatal_optimiaztion.domains.tomato import tomics
from stomatal_optimiaztion.domains.tomato.tomics import alloc, flux, grow


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def test_tomics_namespace_exposes_canonical_names() -> None:
    assert tomics.MODEL_NAME == "TOMICS"
    assert tomics.ALLOC_NAME == "TOMICS-Alloc"
    assert tomics.FLUX_NAME == "TOMICS-Flux"
    assert tomics.GROW_NAME == "TOMICS-Grow"

    assert alloc.MODEL_NAME == "TOMICS-Alloc"
    assert flux.MODEL_NAME == "TOMICS-Flux"
    assert grow.MODEL_NAME == "TOMICS-Grow"

    assert "tomics" in alloc.PARTITION_POLICY_ALIASES
    assert "tomics_hybrid" in alloc.PARTITION_POLICY_ALIASES


def test_canonical_tomics_packages_are_the_only_runtime_surface() -> None:
    alloc_path = Path(alloc.__file__).as_posix()
    flux_path = Path(flux.__file__).as_posix()
    grow_path = Path(grow.__file__).as_posix()

    assert alloc_path.endswith("/domains/tomato/tomics/alloc/__init__.py")
    assert flux_path.endswith("/domains/tomato/tomics/flux/__init__.py")
    assert grow_path.endswith("/domains/tomato/tomics/grow/__init__.py")

    with pytest.raises(ModuleNotFoundError):
        importlib.import_module("stomatal_optimiaztion.domains.tomato.tthorp")
    with pytest.raises(ModuleNotFoundError):
        importlib.import_module("stomatal_optimiaztion.domains.tomato.tgosm")
    with pytest.raises(ModuleNotFoundError):
        importlib.import_module("stomatal_optimiaztion.domains.tomato.ttdgm")


def test_legacy_tomato_package_folders_were_removed() -> None:
    repo_root = _repo_root()
    assert not (repo_root / "src" / "stomatal_optimiaztion" / "domains" / "tomato" / "tthorp").exists()
    assert not (repo_root / "src" / "stomatal_optimiaztion" / "domains" / "tomato" / "tgosm").exists()
    assert not (repo_root / "src" / "stomatal_optimiaztion" / "domains" / "tomato" / "ttdgm").exists()


def test_naming_docs_keep_mapping_and_provenance_notes() -> None:
    repo_root = _repo_root()
    legacy_mapping = (repo_root / "docs" / "legacy_name_mapping.md").read_text(encoding="utf-8")
    migration_doc = (repo_root / "docs" / "architecture" / "tomics-naming-migration.md").read_text(
        encoding="utf-8"
    )
    workspace_audit = (repo_root / "docs" / "architecture" / "00_workspace_audit.md").read_text(
        encoding="utf-8"
    )

    assert "TOMICS-Alloc" in legacy_mapping
    assert "tTHORP" in legacy_mapping
    assert "TOMICS-Flux" in migration_doc
    assert "runtime import" in migration_doc
    assert "retired" in migration_doc
    assert "tTHORP" in workspace_audit
    assert "TOMICS-Alloc" in workspace_audit
