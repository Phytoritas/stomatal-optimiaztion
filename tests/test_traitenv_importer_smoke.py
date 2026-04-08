from __future__ import annotations

import json
import subprocess
import sys
import zipfile
from pathlib import Path

from tests.test_traitenv_loader import _write_traitenv_fixture


def test_import_traitenv_dataset_candidates_script_accepts_zip_bundle(tmp_path: Path) -> None:
    traitenv_root = tmp_path / "traitenv"
    archive_path = tmp_path / "traitenv.zip"
    output_root = tmp_path / "out"
    reviewed_dir = tmp_path / "reviewed"
    _write_traitenv_fixture(traitenv_root)

    with zipfile.ZipFile(archive_path, "w") as archive:
        for file_path in sorted(traitenv_root.iterdir()):
            archive.write(file_path, arcname=file_path.name)

    result = subprocess.run(
        [
            sys.executable,
            "scripts/import_traitenv_dataset_candidates.py",
            "--traitenv-root",
            str(archive_path),
            "--output-root",
            str(output_root),
            "--reviewed-manifest-dir",
            str(reviewed_dir),
        ],
        cwd=Path(__file__).resolve().parents[1],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert (output_root / "dataset_capability_table.csv").exists()
    assert (output_root / "dataset_blocker_report.md").exists()
    assert (output_root / "dataset_registry_snapshot.json").exists()
    assert (reviewed_dir / "traitenv_candidate_registry.json").exists()
    assert (reviewed_dir / "review_template_index.json").exists()
    assert (reviewed_dir / "review_templates" / "school_trait_bundle__yield.review.json").exists()

    snapshot = json.loads((output_root / "dataset_registry_snapshot.json").read_text(encoding="utf-8"))
    dataset_ids = {row["dataset_id"] for row in snapshot["datasets"]}
    assert "school_trait_bundle__yield" in dataset_ids
    assert "public_bigdata_platform__yield_environment" in dataset_ids
