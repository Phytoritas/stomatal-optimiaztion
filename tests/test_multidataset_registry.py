from __future__ import annotations

from pathlib import Path

import yaml

from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.datasets.registry import (
    load_dataset_registry,
)


def test_dataset_registry_loads_explicit_items(tmp_path: Path) -> None:
    config = {
        "validation": {
            "datasets": {
                "default_dataset_ids": ["demo"],
                "items": [
                    {
                        "dataset_id": "demo",
                        "dataset_kind": "fixture",
                        "display_name": "Demo",
                        "forcing_path": "forcing.csv",
                        "observed_harvest_path": "harvest.csv",
                        "validation_start": "2025-01-01",
                        "validation_end": "2025-01-31",
                        "cultivar": "cv",
                        "greenhouse": "gh",
                        "season": "winter",
                        "basis": {"reporting_basis": "floor_area_g_m2", "plants_per_m2": 1.7},
                        "observation": {
                            "date_column": "date",
                            "measured_cumulative_column": "measured",
                        },
                        "priority_tags": ["baseline_window"],
                    }
                ],
            }
        }
    }
    config_path = tmp_path / "config.yaml"
    config_path.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")
    registry = load_dataset_registry(config, repo_root=tmp_path, config_path=config_path)
    assert registry.default_dataset_ids == ("demo",)
    assert registry.require("demo").dataset_kind == "fixture"
    assert registry.to_frame().shape[0] == 1
