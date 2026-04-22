from __future__ import annotations

import json
from pathlib import Path
import zipfile

import pandas as pd
import pytest
import yaml

from stomatal_optimiaztion.domains.tomato.tomics.alloc.core import load_config
from stomatal_optimiaztion.domains.tomato.tomics.alloc.pipelines import resolve_repo_root
from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.current_vs_promoted import (
    prepare_knu_bundle,
)
from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.datasets.contracts import (
    DatasetCapability,
    DatasetIngestionStatus,
)
from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.datasets.registry import (
    load_dataset_registry,
)
from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.traitenv_school_validation import (
    CANONICAL_MEASURED_COLUMN,
    SCHOOL_DATASET_ID,
    build_school_traitenv_validation_bundle,
)


def _xlsx_col_ref(column_idx: int) -> str:
    ref = ""
    current = column_idx + 1
    while current > 0:
        current, remainder = divmod(current - 1, 26)
        ref = chr(65 + remainder) + ref
    return ref


def _write_minimal_first_sheet_xlsx(path: Path, rows: list[list[object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    row_xml: list[str] = []
    for row_idx, row in enumerate(rows, start=1):
        cells: list[str] = []
        for col_idx, value in enumerate(row, start=0):
            if value is None:
                continue
            ref = f"{_xlsx_col_ref(col_idx)}{row_idx}"
            if isinstance(value, str):
                escaped = value.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                cells.append(f'<c r="{ref}" t="inlineStr"><is><t>{escaped}</t></is></c>')
            else:
                cells.append(f'<c r="{ref}"><v>{value}</v></c>')
        row_xml.append(f'<row r="{row_idx}">{"".join(cells)}</row>')

    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr(
            "[Content_Types].xml",
            """<?xml version="1.0" encoding="UTF-8"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>
  <Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
  <Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>
</Types>""",
        )
        archive.writestr(
            "_rels/.rels",
            """<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>
</Relationships>""",
        )
        archive.writestr(
            "xl/workbook.xml",
            """<?xml version="1.0" encoding="UTF-8"?>
<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"
          xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <sheets>
    <sheet name="Sheet1" sheetId="1" r:id="rId1"/>
  </sheets>
</workbook>""",
        )
        archive.writestr(
            "xl/_rels/workbook.xml.rels",
            """<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>
  <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>
</Relationships>""",
        )
        archive.writestr(
            "xl/styles.xml",
            """<?xml version="1.0" encoding="UTF-8"?>
<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
  <fonts count="1"><font><sz val="11"/><name val="Calibri"/></font></fonts>
  <fills count="1"><fill><patternFill patternType="none"/></fill></fills>
  <borders count="1"><border/></borders>
  <cellStyleXfs count="1"><xf/></cellStyleXfs>
  <cellXfs count="1"><xf numFmtId="0"/></cellXfs>
</styleSheet>""",
        )
        archive.writestr(
            "xl/worksheets/sheet1.xml",
            """<?xml version="1.0" encoding="UTF-8"?>
<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
  <sheetData>"""
            + "".join(row_xml)
            + """</sheetData>
</worksheet>""",
        )


def _write_school_common_workbook(raw_repo_root: Path) -> Path:
    workbook_path = (
        raw_repo_root
        / "40_\uc791\uc5c5\u00b7\uc7ac\ubc30\uc815\ubcf4"
        / "\ud1a0\ub9c8\ud1a0_\uc7ac\ubc30\uc815\ubcf4_\uacf5\ud1b5.xlsx"
    )
    _write_minimal_first_sheet_xlsx(
        workbook_path,
        rows=[
            [
                "\uc0dd\uc721\uc870\uc0ac \ud56d\ubaa9",
                "\ud488\uc885",
                "\ucc98\ub9ac",
                "\ucc98\ub9ac \uc2dc\uc791",
                "\ucc98\ub9ac \uc885\ub8cc",
                "Control",
                "Drought",
                "\uc0d8\ud50c\ub9c1 \ub0a0\uc9dc",
                "\ud30c\uc885, \ud050\ube0c \uac00\uc2dd, \uc815\uc2dd, \uccab\uc218\ud655",
                "\uc791\uae30 \uc2dc\uc791",
                "\uc791\uae30 \uc885\ub8cc",
                "\uc7ac\ubc30\uba74\uc801(m2)",
                "\uc7ac\uc2dd\ubc00\ub3c4(plants/m2)",
            ],
            [
                "2024\ub144 \uc791\uae30",
                "\ub300\ud504\ub2c8\uc2a4",
                "Control (A,B,C,D)",
                "-",
                "-",
                "-",
                "-",
                "5\uc6d4 9\uc77c, 6\uc6d4 13\uc77c, 8\uc6d4 8\uc77c",
                "5\uc6d4 9\uc77c, \ud050\ube0c \uc0ac\uc6a9X, 6\uc6d4 13\uc77c, 8\uc6d4 8\uc77c",
                45456,
                45644,
                100.757525,
                1.9849634059590089,
            ],
        ],
    )
    return workbook_path


def _write_school_traitenv_private_fixture(root: Path, *, notes_only_crop_metadata: bool = False) -> None:
    crop_dir = (
        root
        / "partitioned_csv"
        / "integrated_observations"
        / "dataset_family=school_crop_info"
        / "observation_family=metadata"
    )
    env_dir = (
        root
        / "partitioned_csv"
        / "integrated_observations"
        / "dataset_family=school_greenhouse_environment"
        / "observation_family=environment"
    )
    yield_dir = (
        root
        / "partitioned_csv"
        / "comparison_daily"
        / "dataset_family=school_trait_bundle"
        / "observation_family=yield"
    )
    crop_dir.mkdir(parents=True, exist_ok=True)
    env_dir.mkdir(parents=True, exist_ok=True)
    yield_dir.mkdir(parents=True, exist_ok=True)

    pd.DataFrame(
        [
            {
                "season_label": "2024",
                "treatment": "Control (A,B)",
                "cultivar": "Dafnis",
                "crop_start": None if notes_only_crop_metadata else "2024-08-01",
                "crop_end": None if notes_only_crop_metadata else "2024-08-21",
                "season_notes": "5/9 sowing, 6/13 transplant, 8/8 first harvest",
                "crop_area_m2": None if notes_only_crop_metadata else 100.0,
                "plants_per_m2": None if notes_only_crop_metadata else 2.0,
            }
        ]
    ).to_csv(crop_dir / "data.csv", index=False)

    env_rows: list[dict[str, object]] = []
    for idx, ts in enumerate(pd.date_range("2024-08-01", "2024-08-21", freq="D"), start=1):
        env_rows.append(
            {
                "season_label": "2024",
                "Timestamp": ts.strftime("%Y-%m-%d 00:00:00"),
                "Air temperature (째C)_mean": 24.0 + idx * 0.1,
                "Inside radiation intensity (W/m2)_mean": 150.0 + idx,
                "CO2 (ppm)_mean": 420.0 + idx,
                "RH (%)_mean": 70.0 - idx * 0.2,
                "Wind speed (m/s)_mean": 0.5 + idx * 0.01,
            }
        )
    pd.DataFrame(env_rows).to_csv(env_dir / "data.csv", index=False)

    yield_rows: list[dict[str, object]] = []
    for ts in pd.date_range("2024-08-08", "2024-08-21", freq="D"):
        for entity, value in (("A", 100.0), ("B", 200.0)):
            yield_rows.append(
                {
                    "season_label": "2024",
                    "treatment": "Control",
                    "comparison_entity": entity,
                    "comparison_date": ts.strftime("%Y-%m-%d"),
                    "standard_name": "total_yield_weight_g",
                    "aggregation_stat": "sum",
                    "value_sum": value,
                }
            )
    pd.DataFrame(yield_rows).to_csv(yield_dir / "data.csv", index=False)


def test_school_traitenv_bundle_stays_review_only_without_explicit_approval(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    traitenv_root = tmp_path / "traitenv"
    output_root = tmp_path / "bundle-review"
    _write_school_traitenv_private_fixture(traitenv_root)

    bundle = build_school_traitenv_validation_bundle(
        traitenv_root=traitenv_root,
        output_root=output_root,
        repo_root=repo_root,
        approve_runnable_contract=False,
    )

    yield_df = pd.read_csv(bundle.yield_csv_path)
    assert bundle.dataset_overlay["dry_matter_conversion"]["review_only"] is True
    assert yield_df[CANONICAL_MEASURED_COLUMN].iloc[-1] == pytest.approx(14 * ((300.0 / 100.0) * 0.065))

    config = load_config(bundle.generated_config_paths["multidataset_factorial_config"])
    registry = load_dataset_registry(
        config,
        repo_root=repo_root,
        config_path=bundle.generated_config_paths["multidataset_factorial_config"],
    )
    school_dataset = registry.require(SCHOOL_DATASET_ID)
    manifest = json.loads(bundle.manifest_path.read_text(encoding="utf-8"))

    assert school_dataset.capability is DatasetCapability.MEASURED_HARVEST
    assert school_dataset.ingestion_status is DatasetIngestionStatus.DRAFT_NEEDS_HARVEST_MAPPING
    assert school_dataset.is_runnable_measured_harvest is False
    assert "review_only_dry_matter_conversion" in school_dataset.blocker_codes
    assert bundle.dataset_overlay["notes"]["private_derivation_official_mode"] == "manual_reviewed_derivative"
    assert bundle.dataset_overlay["notes"]["private_derivation_public_promotion_default"] == "unchanged"
    assert manifest["workflow_contract"]["official_mode"] == "manual_reviewed_derivative"
    assert manifest["workflow_contract"]["generated_private_overlay_is_locally_runnable"] is False
    assert manifest["workflow_contract"]["public_promotion_semantics_unchanged"] is True


def test_school_traitenv_bundle_can_become_runnable_with_explicit_private_approval(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    traitenv_root = tmp_path / "traitenv"
    output_root = tmp_path / "bundle-approved"
    _write_school_traitenv_private_fixture(traitenv_root)

    bundle = build_school_traitenv_validation_bundle(
        traitenv_root=traitenv_root,
        output_root=output_root,
        repo_root=repo_root,
        approve_runnable_contract=True,
    )

    config = load_config(bundle.generated_config_paths["multidataset_factorial_config"])
    registry = load_dataset_registry(
        config,
        repo_root=repo_root,
        config_path=bundle.generated_config_paths["multidataset_factorial_config"],
    )
    school_dataset = registry.require(SCHOOL_DATASET_ID)
    registry_frame = registry.to_frame()
    school_row = registry_frame.loc[registry_frame["dataset_id"] == SCHOOL_DATASET_ID].iloc[0]

    assert school_dataset.is_runnable_measured_harvest is True
    assert school_dataset.blocker_codes == ()
    assert school_dataset.observation.measured_cumulative_column == CANONICAL_MEASURED_COLUMN
    assert school_dataset.notes["dataset_role_hint"] == "measured_harvest_runnable"
    assert school_dataset.notes["observed_harvest_derivation"] == "derived_dw_from_measured_fresh_school_harvest"
    assert school_dataset.notes["is_direct_dry_weight"] is False
    assert school_dataset.notes["uses_literature_dry_matter_fraction"] is True
    assert school_dataset.notes["dry_weight_derivation_review_grade"] == "manual_reviewed_private"
    assert SCHOOL_DATASET_ID in config["validation"]["datasets"]["default_dataset_ids"]
    assert school_row["dry_weight_derivation_review_grade"] == "manual_reviewed_private"


def test_school_traitenv_generated_current_config_resolves_repo_root_and_prepares_bundle(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    traitenv_root = tmp_path / "traitenv"
    output_root = tmp_path / "bundle-config"
    _write_school_traitenv_private_fixture(traitenv_root)

    bundle = build_school_traitenv_validation_bundle(
        traitenv_root=traitenv_root,
        output_root=output_root,
        repo_root=repo_root,
        approve_runnable_contract=True,
    )

    current_config_path = bundle.generated_config_paths["current_vs_promoted_config"]
    current_config = yaml.safe_load(current_config_path.read_text(encoding="utf-8"))

    assert Path(current_config["paths"]["repo_root"]).resolve() == repo_root.resolve()
    assert Path(current_config["validation"]["forcing_csv_path"]).resolve() == bundle.forcing_csv_path.resolve()
    assert Path(current_config["validation"]["yield_xlsx_path"]).resolve() == bundle.yield_csv_path.resolve()

    loaded_config = load_config(current_config_path)
    resolved_repo_root = resolve_repo_root(loaded_config, config_path=current_config_path)
    prepared_bundle = prepare_knu_bundle(loaded_config, repo_root=resolved_repo_root, config_path=current_config_path)

    assert prepared_bundle.validation_start.date().isoformat() == "2024-08-08"
    assert prepared_bundle.validation_end.date().isoformat() == "2024-08-21"
    assert Path(prepared_bundle.data_contract.forcing_path).resolve() == bundle.forcing_csv_path.resolve()
    assert Path(prepared_bundle.data_contract.yield_path).resolve() == bundle.yield_csv_path.resolve()


def test_school_traitenv_bundle_falls_back_to_raw_common_workbook_for_basis_metadata(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    traitenv_root = tmp_path / "traitenv"
    raw_repo_root = tmp_path / "raw-tomato"
    output_root = tmp_path / "bundle-raw-workbook"
    _write_school_traitenv_private_fixture(traitenv_root, notes_only_crop_metadata=True)
    workbook_path = _write_school_common_workbook(raw_repo_root)

    bundle = build_school_traitenv_validation_bundle(
        traitenv_root=traitenv_root,
        output_root=output_root,
        repo_root=repo_root,
        raw_repo_root=raw_repo_root,
        approve_runnable_contract=True,
    )
    manifest = json.loads(bundle.manifest_path.read_text(encoding="utf-8"))

    assert bundle.area_m2 == pytest.approx(100.757525)
    assert bundle.plants_per_m2 == pytest.approx(1.9849634059590089)
    assert bundle.crop_start == "2024-06-13"
    assert bundle.crop_end == "2024-12-18"
    source_paths = bundle.dataset_overlay["notes"]["private_derivation_source_paths"]
    assert Path(source_paths["crop_common_workbook_path"]).resolve() == workbook_path.resolve()
    assert source_paths["raw_repo_resolution_mode"] == "explicit_arg"
    assert bundle.dataset_overlay["notes"]["private_derivation_crop_context"]["metadata_source_kind"] == "raw_common_workbook"
    assert manifest["workflow_contract"]["raw_repo_resolution_mode"] == "explicit_arg"


def test_school_traitenv_bundle_resolves_raw_workbook_from_source_origin_manifest(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    traitenv_root = tmp_path / "traitenv"
    raw_repo_root = tmp_path / "raw-tomato"
    output_root = tmp_path / "bundle-source-origin"
    _write_school_traitenv_private_fixture(traitenv_root, notes_only_crop_metadata=True)
    workbook_path = _write_school_common_workbook(raw_repo_root)
    (traitenv_root / ".source_origin.json").write_text(
        json.dumps(
            {
                "source_traitenv_root": str(traitenv_root.resolve()),
                "source_raw_repo_root": str(raw_repo_root.resolve()),
            },
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )

    bundle = build_school_traitenv_validation_bundle(
        traitenv_root=traitenv_root,
        output_root=output_root,
        repo_root=repo_root,
        approve_runnable_contract=True,
    )
    manifest = json.loads(bundle.manifest_path.read_text(encoding="utf-8"))

    assert bundle.area_m2 == pytest.approx(100.757525)
    assert bundle.plants_per_m2 == pytest.approx(1.9849634059590089)
    source_paths = bundle.dataset_overlay["notes"]["private_derivation_source_paths"]
    assert source_paths["raw_repo_resolution_mode"] == "source_origin_manifest"
    assert Path(source_paths["source_origin_manifest_path"]).resolve() == (traitenv_root / ".source_origin.json").resolve()
    assert Path(source_paths["crop_common_workbook_path"]).resolve() == workbook_path.resolve()
    assert manifest["source_paths"]["raw_repo_resolution_mode"] == "source_origin_manifest"
    assert Path(manifest["workflow_contract"]["source_origin_manifest_path"]).resolve() == (
        traitenv_root / ".source_origin.json"
    ).resolve()
