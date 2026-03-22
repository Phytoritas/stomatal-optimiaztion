from __future__ import annotations

import json

import pandas as pd

from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.harvest_family_eval import (
    summarize_family_state_coverage,
)


def test_summarize_family_state_coverage_tracks_mixed_native_and_proxy_days() -> None:
    coverage = summarize_family_state_coverage(
        pd.DataFrame(
            {
                "date": pd.to_datetime(["2024-08-08", "2024-08-09", "2024-08-10"]),
                "native_family_state_fraction": [1.0, 0.25, 0.0],
                "proxy_family_state_fraction": [0.0, 0.75, 1.0],
                "shared_tdvs_proxy_flag": [False, False, True],
                "family_state_mode": [
                    "native_payload",
                    "dekoning_runtime_reconstruction",
                    "shared_tdvs_proxy",
                ],
                "proxy_mode_used": [False, True, True],
            }
        ),
        observed_dates=pd.Series(pd.to_datetime(["2024-08-08", "2024-08-09", "2024-08-10"])),
    )

    assert coverage["native_family_state_fraction"] == 0.4166666666666667
    assert coverage["proxy_family_state_fraction"] == 0.5833333333333334
    assert coverage["shared_tdvs_proxy_fraction"] == 0.3333333333333333
    assert coverage["family_state_mode"] == "dekoning_runtime_reconstruction"

    family_distribution = json.loads(str(coverage["family_state_mode_distribution"]))
    proxy_distribution = json.loads(str(coverage["proxy_mode_used_distribution"]))

    assert family_distribution["shared_tdvs_proxy"] > 0.0
    assert family_distribution["native_payload"] > 0.0
    assert proxy_distribution["true"] == 2.0 / 3.0
    assert proxy_distribution["false"] == 1.0 / 3.0
