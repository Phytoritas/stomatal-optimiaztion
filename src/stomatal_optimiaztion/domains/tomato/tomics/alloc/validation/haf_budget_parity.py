from __future__ import annotations

import pandas as pd


STAGE_BUDGET_UNITS = {
    "HF0": 0,
    "HF1": 4,
    "HF2": 6,
    "HF3": 8,
    "HF4": 8,
}
GROUP_BUDGET_LIMITS = {
    "none": 0,
    "equal_budget_low": 6,
    "equal_budget_medium": 10,
    "parity_audit_only": 10,
}
BUDGET_PARITY_BASIS = "knob_count_and_hidden_calibration_budget"
BUDGET_PARITY_LIMITATIONS = (
    "Budget parity counts harvest, observation-operator, latent-prior, and "
    "hidden-calibration knobs; it does not evaluate wall-clock compute-budget parity."
)


def build_haf_budget_parity_frame(design_df: pd.DataFrame) -> pd.DataFrame:
    if design_df.empty:
        return pd.DataFrame()
    frame = design_df.copy()
    frame["stage_budget_units"] = frame["stage"].map(STAGE_BUDGET_UNITS).fillna(0).astype(int)
    frame["harvest_knobs_count"] = frame["stage"].map(
        {"HF0": 0, "HF1": 2, "HF2": 2, "HF3": 4, "HF4": 4}
    ).fillna(0)
    frame["observation_operator_knobs_count"] = 1
    frame["latent_allocation_prior_knobs_count"] = (
        frame["allocator_family"].eq("tomics_haf_latent_allocation_research")
        & frame["latent_allocation_prior_family"].ne("none")
    ).astype(int)
    extra_raw = (
        frame["extra_calibration_budget_units"]
        if "extra_calibration_budget_units" in frame.columns
        else pd.Series(0, index=frame.index)
    )
    extra_units = pd.to_numeric(extra_raw, errors="coerce").fillna(0).astype(int)
    frame["extra_calibration_budget_units"] = extra_units
    frame["extra_calibration_budget_flag"] = extra_units.gt(0)
    frame["budget_parity_group"] = frame["stage"].map(
        {
            "HF0": "none",
            "HF1": "equal_budget_low",
            "HF2": "equal_budget_medium",
            "HF3": "equal_budget_medium",
            "HF4": "parity_audit_only",
        }
    )
    frame["budget_units_used"] = (
        frame["stage_budget_units"]
        + frame["latent_allocation_prior_knobs_count"]
        + frame["extra_calibration_budget_units"]
    )
    frame["budget_limit_units"] = frame["budget_parity_group"].map(GROUP_BUDGET_LIMITS).fillna(0).astype(int)
    frame["budget_parity_violation"] = frame["budget_units_used"].gt(frame["budget_limit_units"])
    frame["budget_penalty"] = frame["budget_parity_violation"].astype(float) * 1_000.0
    frame["budget_parity_basis"] = BUDGET_PARITY_BASIS
    frame["wall_clock_compute_budget_parity_evaluated"] = False
    frame["wall_clock_compute_budget_parity_required_for_goal_3b"] = False
    frame["budget_parity_limitations"] = BUDGET_PARITY_LIMITATIONS
    return frame[
        [
            "candidate_id",
            "stage",
            "allocator_family",
            "latent_allocation_prior_family",
            "fruit_harvest_family",
            "leaf_harvest_family",
            "observation_operator",
            "fdmc_mode",
            "budget_units_used",
            "budget_limit_units",
            "budget_parity_group",
            "harvest_knobs_count",
            "observation_operator_knobs_count",
            "latent_allocation_prior_knobs_count",
            "extra_calibration_budget_flag",
            "budget_parity_violation",
            "budget_penalty",
            "budget_parity_basis",
            "wall_clock_compute_budget_parity_evaluated",
            "wall_clock_compute_budget_parity_required_for_goal_3b",
            "budget_parity_limitations",
        ]
    ].copy()


__all__ = [
    "BUDGET_PARITY_BASIS",
    "BUDGET_PARITY_LIMITATIONS",
    "STAGE_BUDGET_UNITS",
    "build_haf_budget_parity_frame",
]
