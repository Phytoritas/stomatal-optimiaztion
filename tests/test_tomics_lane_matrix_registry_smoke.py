from __future__ import annotations

from pathlib import Path

import pytest

from stomatal_optimiaztion.domains.tomato.tomics.alloc.core import load_config
from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.current_vs_promoted import (
    run_current_vs_promoted_factorial,
)
from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.harvest_calibration_bridge import (
    load_harvest_candidates,
)
from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.lane_matrix import (
    resolve_allocation_lanes,
)

from .tomics_knu_test_helpers import write_minimal_knu_config


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


@pytest.mark.slow
def test_allocation_lane_registry_resolves_current_vs_promoted_candidates_smoke(tmp_path: Path) -> None:
    repo_root = _repo_root()
    config_path = write_minimal_knu_config(tmp_path, repo_root=repo_root, mode="both")
    run_current_vs_promoted_factorial(config_path=config_path, mode="both")
    config = load_config(config_path)
    candidates, _ = load_harvest_candidates(config=config, repo_root=repo_root, config_path=config_path)
    lanes = {lane.lane_id: lane for lane in resolve_allocation_lanes(candidates)}

    assert lanes["legacy_sink_baseline"].partition_policy == "legacy"
    assert lanes["incumbent_current"].partition_policy == "tomics"
    assert lanes["research_current"].partition_policy == "tomics_alloc_research"
    assert lanes["research_promoted"].partition_policy == "tomics_promoted_research"
    assert lanes["raw_reference_thorp"].partition_policy == "thorp_fruit_veg"
    assert lanes["legacy_sink_baseline"].architecture_id != lanes["incumbent_current"].architecture_id
