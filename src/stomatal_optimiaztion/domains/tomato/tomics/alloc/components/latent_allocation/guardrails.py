from __future__ import annotations

from typing import Any

import pandas as pd

from stomatal_optimiaztion.domains.tomato.tomics.alloc.components.latent_allocation.contracts import (
    allocation_bounds,
    as_dict,
)


def _row_count(mask: pd.Series) -> int:
    return int(mask.fillna(False).sum())


def _guardrail_row(
    name: str,
    violation_count: int,
    *,
    max_violation: float = 0.0,
    affected_rows: str = "",
    notes: str = "",
) -> dict[str, Any]:
    passed = violation_count == 0
    return {
        "guardrail_name": name,
        "status": "pass" if passed else "fail",
        "pass_fail": bool(passed),
        "violation_count": int(violation_count),
        "max_violation": float(max_violation),
        "affected_rows": affected_rows,
        "notes": notes,
    }


def _affected(mask: pd.Series, frame: pd.DataFrame) -> str:
    if not bool(mask.any()):
        return ""
    keep = [column for column in ("date", "loadcell_id", "treatment", "prior_family") if column in frame.columns]
    return frame.loc[mask, keep].head(10).to_json(orient="records")


def evaluate_latent_allocation_guardrails(
    posteriors: pd.DataFrame,
    metadata: dict[str, Any],
    config: dict[str, Any],
) -> pd.DataFrame:
    bounds = allocation_bounds(config)
    latent_cfg = as_dict(config.get("latent_allocation"))
    stress_cfg = as_dict(latent_cfg.get("stress_gates"))
    wet_threshold = float(stress_cfg.get("wet_rzi_threshold", 0.05))
    activation = float(stress_cfg.get("rzi_activation_threshold", 0.15))
    tol = 1e-6
    if posteriors.empty:
        return pd.DataFrame(
            [
                _guardrail_row(
                    "latent_allocation_outputs_present",
                    1,
                    notes="No posterior rows were produced.",
                )
            ]
        )

    rows: list[dict[str, Any]] = []
    leaf_mask = posteriors["inferred_u_leaf"] < bounds.leaf_floor - tol
    rows.append(
        _guardrail_row(
            "no_leaf_collapse",
            _row_count(leaf_mask),
            max_violation=float((bounds.leaf_floor - posteriors.loc[leaf_mask, "inferred_u_leaf"]).max()) if leaf_mask.any() else 0.0,
            affected_rows=_affected(leaf_mask, posteriors),
            notes="Leaf floor applies because direct organ partition evidence is absent.",
        )
    )

    wet_mask = posteriors["RZI_main"].fillna(0.0) <= wet_threshold
    wet_violation = wet_mask & (posteriors["inferred_u_root"] > bounds.wet_root_cap + tol)
    rows.append(
        _guardrail_row(
            "no_wet_root_excess",
            _row_count(wet_violation),
            max_violation=float((posteriors.loc[wet_violation, "inferred_u_root"] - bounds.wet_root_cap).max())
            if wet_violation.any()
            else 0.0,
            affected_rows=_affected(wet_violation, posteriors),
            notes="Wet-condition root excess is forbidden.",
        )
    )

    root_increase = posteriors["inferred_u_root"] > posteriors["legacy_prior_u_root"] + tol
    stress_violation = root_increase & (posteriors["RZI_main"].fillna(0.0) < activation)
    rows.append(
        _guardrail_row(
            "stress_gated_root_increase",
            _row_count(stress_violation),
            max_violation=float(
                (posteriors.loc[stress_violation, "inferred_u_root"] - posteriors.loc[stress_violation, "legacy_prior_u_root"]).max()
            )
            if stress_violation.any()
            else 0.0,
            affected_rows=_affected(stress_violation, posteriors),
            notes="Root allocation increase above legacy prior requires root-zone stress support.",
        )
    )

    lai_low = posteriors.get("LAI_proxy_available", pd.Series(False, index=posteriors.index)).fillna(False) & (
        posteriors.get("LAI_proxy_value", pd.Series(3.0, index=posteriors.index)).fillna(3.0) < 3.0
    )
    lai_violation = lai_low & (posteriors["inferred_u_leaf"] < bounds.leaf_floor - tol)
    rows.append(
        _guardrail_row(
            "LAI_protection",
            _row_count(lai_violation),
            affected_rows=_affected(lai_violation, posteriors),
            notes="LAI unavailable rows use only the explicit configured LAI proxy.",
        )
    )

    fruit_violation = posteriors["inferred_u_fruit"] < posteriors["legacy_prior_u_fruit"] - tol
    rows.append(
        _guardrail_row(
            "fruit_gate_preservation",
            _row_count(fruit_violation),
            max_violation=float(
                (posteriors.loc[fruit_violation, "legacy_prior_u_fruit"] - posteriors.loc[fruit_violation, "inferred_u_fruit"]).max()
            )
            if fruit_violation.any()
            else 0.0,
            affected_rows=_affected(fruit_violation, posteriors),
            notes="Tomato-first fruit-vs-vegetative gate remains primary.",
        )
    )

    raw_thorp_violation = bool(metadata.get("raw_THORP_allocator_used", False)) or bool(
        posteriors.get("raw_THORP_allocator_used", pd.Series(False, index=posteriors.index)).fillna(False).any()
    )
    rows.append(
        _guardrail_row(
            "no_raw_THORP",
            int(raw_thorp_violation),
            notes="THORP may appear only as a bounded prior/correction or diagnostic comparator.",
        )
    )

    sum_violation = posteriors["allocation_sum_error"] > 1e-6
    rows.append(
        _guardrail_row(
            "sum_to_one",
            _row_count(sum_violation),
            max_violation=float(posteriors.loc[sum_violation, "allocation_sum_error"].max()) if sum_violation.any() else 0.0,
            affected_rows=_affected(sum_violation, posteriors),
        )
    )

    fruit_calibration_violation = bool(metadata.get("fruit_diameter_allocation_calibration_target", False)) or bool(
        metadata.get("fruit_diameter_p_values_allowed", False)
    )
    rows.append(
        _guardrail_row(
            "no_fruit_diameter_calibration",
            int(fruit_calibration_violation),
            notes="Fruit diameter appears only as diagnostic observer, never target/calibration/promotion.",
        )
    )

    direct_validation_violation = bool(metadata.get("latent_allocation_directly_validated", False)) or bool(
        metadata.get("direct_partition_observation_available", False)
    )
    rows.append(
        _guardrail_row(
            "no_direct_validation_claim",
            int(direct_validation_violation),
            notes="Direct organ partition observations are unavailable.",
        )
    )
    return pd.DataFrame(rows)


__all__ = ["evaluate_latent_allocation_guardrails"]
