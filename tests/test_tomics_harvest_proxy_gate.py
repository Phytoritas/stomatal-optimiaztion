from __future__ import annotations

import pandas as pd

from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.harvest_promotion_gate import (
    proxy_coverage_guardrail,
)


def test_proxy_coverage_guardrail_blocks_proxy_heavy_winner() -> None:
    guardrail = proxy_coverage_guardrail(
        pd.Series(
            {
                "mean_native_family_state_fraction": 0.20,
                "mean_proxy_family_state_fraction": 0.80,
                "mean_shared_tdvs_proxy_fraction": 0.75,
            }
        ),
        native_state_coverage_min=0.5,
        shared_tdvs_proxy_fraction_max=0.5,
    )

    assert guardrail["winner_proxy_heavy_flag"] is True
    assert guardrail["winner_not_promotion_grade_due_to_proxy_dependence"] is True


def test_proxy_coverage_guardrail_allows_native_leaning_winner() -> None:
    guardrail = proxy_coverage_guardrail(
        pd.Series(
            {
                "mean_native_family_state_fraction": 0.75,
                "mean_proxy_family_state_fraction": 0.25,
                "mean_shared_tdvs_proxy_fraction": 0.10,
            }
        ),
        native_state_coverage_min=0.5,
        shared_tdvs_proxy_fraction_max=0.5,
    )

    assert guardrail["winner_proxy_heavy_flag"] is False
    assert guardrail["winner_not_promotion_grade_due_to_proxy_dependence"] is False
