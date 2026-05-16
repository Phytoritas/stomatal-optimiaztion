from pathlib import Path

import pandas as pd

from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.haf_plotkit_manifest import (
    FRAME_ROLE_FILES,
    write_haf_plotkit_render_manifest,
)
from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.haf_pre_gate_artifacts import (
    REQUIRED_PLOTKIT_BUNDLES,
)


def test_haf_plotkit_manifest_validates_required_scaffold_specs(
    tmp_path: Path,
) -> None:
    spec_dir = Path("configs/plotkit/tomics/haf_2025_2c")
    for bundle in REQUIRED_PLOTKIT_BUNDLES:
        assert (spec_dir / f"{bundle}.yaml").exists()

    input_root = tmp_path / "inputs"
    input_root.mkdir()
    for filename in set(FRAME_ROLE_FILES.values()):
        (input_root / filename).write_text("candidate_id,value\nx,1\n", encoding="utf-8")

    paths = write_haf_plotkit_render_manifest(
        spec_dir=spec_dir,
        input_root=input_root,
        output_root=tmp_path / "figures",
    )
    manifest = pd.read_csv(paths["plotkit_render_manifest_csv"])
    required = manifest[manifest["bundle"].isin(REQUIRED_PLOTKIT_BUNDLES)]

    assert set(required["bundle"]) == set(REQUIRED_PLOTKIT_BUNDLES)
    assert required["render_status"].isin(
        {
            "rendered",
            "spec_validated_only",
            "failed_missing_renderer",
            "failed_missing_data",
        }
    ).all()
    assert required["render_status"].eq("spec_validated_only").all()
    assert not any((tmp_path / "figures").glob("*.png"))
