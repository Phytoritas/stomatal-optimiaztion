from __future__ import annotations

import json
from pathlib import Path

import yaml

from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.data_contract import (
    resolve_knu_data_contract,
    write_data_contract_manifest,
)
from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.knu_data import load_knu_validation_data


def test_knu_data_contract_resolves_private_root_and_writes_manifest(tmp_path: Path, monkeypatch) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    private_root = tmp_path / "private_root" / "data" / "forcing"
    private_root.mkdir(parents=True, exist_ok=True)
    forcing_fixture = repo_root / "tests" / "fixtures" / "knu_sanitized" / "KNU_Tomato_Env_fixture.csv"
    yield_fixture = repo_root / "tests" / "fixtures" / "knu_sanitized" / "tomato_validation_data_yield_fixture.csv"
    (private_root / "KNU_Tomato_Env.CSV").write_text(forcing_fixture.read_text(encoding="utf-8"), encoding="utf-8")
    (private_root / "tomato_validation_data_yield_260222.csv").write_text(
        yield_fixture.read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    contract_path = tmp_path / "contract.yaml"
    contract_path.write_text(
        yaml.safe_dump(
            {
                "private_data_root_env": "PHYTORITAS_PRIVATE_DATA_ROOT",
                "forcing_relative_path": "data/forcing/KNU_Tomato_Env.CSV",
                "yield_relative_path": "data/forcing/tomato_validation_data_yield_260222.csv",
                "reporting_basis": "floor_area_g_m2",
                "plants_per_m2": 1.836091,
            },
            sort_keys=False,
            allow_unicode=False,
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("PHYTORITAS_PRIVATE_DATA_ROOT", str(tmp_path / "private_root"))
    validation_cfg = {
        "forcing_csv_path": "missing/KNU_Tomato_Env.CSV",
        "yield_xlsx_path": "missing/tomato_validation_data_yield_260222.csv",
        "private_data_contract_path": str(contract_path),
    }
    contract = resolve_knu_data_contract(validation_cfg=validation_cfg, repo_root=repo_root, config_path=contract_path)
    assert contract.forcing_source_kind == "private_root"
    assert contract.yield_source_kind == "private_root"
    data = load_knu_validation_data(forcing_path=contract.forcing_path, yield_path=contract.yield_path)
    manifest_path = write_data_contract_manifest(output_root=tmp_path / "out", contract=contract, data=data)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["reporting_basis"] == "floor_area_g_m2"
    assert manifest["plants_per_m2"] == 1.836091
    assert manifest["parser_assumptions"]["observation_semantics"] == "cumulative_harvested_fruit_dry_weight_floor_area"
