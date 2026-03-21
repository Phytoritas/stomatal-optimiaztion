from __future__ import annotations

from dataclasses import dataclass
import pandas as pd

from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.knu_data import PLANTS_PER_M2


@dataclass(frozen=True, slots=True)
class ReconstructionCandidate:
    mode: str
    label: str
    initial_state_overrides: dict[str, object]


def _baseline_leaf_mass_from_lai(lai_value: float, *, sla_m2_g: float = 0.022) -> float:
    return max(float(lai_value) / max(float(sla_m2_g), 1e-6), 1.0)


def _fruit_cohorts(
    *,
    fruit_mass_g_m2: float,
    active_trusses: int,
    n_fruits_per_truss: int = 4,
    shoots_per_m2: float = PLANTS_PER_M2,
) -> list[dict[str, object]]:
    if active_trusses <= 0 or fruit_mass_g_m2 <= 0.0:
        return []
    weights = [float(idx + 1) for idx in range(active_trusses)]
    total_weight = sum(weights)
    tdvs_values = [0.35 + 0.55 * idx / max(active_trusses - 1, 1) for idx in range(active_trusses)]
    cohorts: list[dict[str, object]] = []
    for idx in range(active_trusses):
        cohorts.append(
            {
                "tdvs": min(tdvs_values[idx], 0.98),
                "n_fruits": n_fruits_per_truss,
                "w_fr_cohort": fruit_mass_g_m2 * weights[idx] / total_weight,
                "active": True,
                "mult": shoots_per_m2,
            }
        )
    return cohorts


def build_reconstruction_candidates(
    observed_df: pd.DataFrame,
    *,
    modes: tuple[str, ...] = ("minimal_scalar_init", "cohort_aware_init", "buffer_aware_init"),
    shoots_per_m2: float = PLANTS_PER_M2,
) -> list[ReconstructionCandidate]:
    measured = pd.to_numeric(
        observed_df["measured_cumulative_total_fruit_dry_weight_floor_area"],
        errors="coerce",
    )
    increments = pd.to_numeric(observed_df["measured_daily_increment_floor_area"], errors="coerce").dropna()
    first_measured = float(measured.iloc[0]) if not measured.empty else 0.0
    mean_increment = float(increments.clip(lower=0.0).head(5).mean()) if not increments.empty else 2.0
    if not pd.notna(mean_increment) or mean_increment <= 0.0:
        mean_increment = 2.0

    lai_targets = (2.0, 2.6)
    fruit_levels = (
        max(mean_increment * 2.5, 6.0),
        max(mean_increment * 4.5, 12.0),
    )
    candidates: list[ReconstructionCandidate] = []

    if "minimal_scalar_init" in modes:
        for lai_target in lai_targets:
            leaf_mass = _baseline_leaf_mass_from_lai(lai_target)
            for fruit_mass in fruit_levels:
                candidates.append(
                    ReconstructionCandidate(
                        mode="minimal_scalar_init",
                        label=f"minimal_lai_{lai_target:.1f}_fruit_{fruit_mass:.1f}",
                        initial_state_overrides={
                            "LAI": lai_target,
                            "W_lv": leaf_mass,
                            "W_st": leaf_mass * 0.45,
                            "W_rt": leaf_mass * 0.30,
                            "W_fr": fruit_mass,
                            "W_fr_harvested": first_measured,
                        },
                    )
                )

    if "cohort_aware_init" in modes:
        for lai_target in lai_targets:
            leaf_mass = _baseline_leaf_mass_from_lai(lai_target)
            for active_trusses in (4, 6):
                for fruit_mass in fruit_levels:
                    candidates.append(
                        ReconstructionCandidate(
                            mode="cohort_aware_init",
                            label=f"cohort_lai_{lai_target:.1f}_truss_{active_trusses}_fruit_{fruit_mass:.1f}",
                            initial_state_overrides={
                                "LAI": lai_target,
                                "W_lv": leaf_mass,
                                "W_st": leaf_mass * 0.48,
                                "W_rt": leaf_mass * 0.32,
                                "W_fr_harvested": first_measured,
                                "truss_cohorts": _fruit_cohorts(
                                    fruit_mass_g_m2=fruit_mass,
                                    active_trusses=active_trusses,
                                    shoots_per_m2=shoots_per_m2,
                                ),
                                "truss_count": active_trusses,
                                "n_f": 4,
                            },
                        )
                    )

    if "buffer_aware_init" in modes:
        for lai_target in lai_targets:
            leaf_mass = _baseline_leaf_mass_from_lai(lai_target)
            for reserve_pool in (6.0, 12.0):
                fruit_mass = max(mean_increment * 3.5, 10.0)
                candidates.append(
                    ReconstructionCandidate(
                        mode="buffer_aware_init",
                        label=f"buffer_lai_{lai_target:.1f}_reserve_{reserve_pool:.1f}",
                        initial_state_overrides={
                            "LAI": lai_target,
                            "W_lv": leaf_mass,
                            "W_st": leaf_mass * 0.46,
                            "W_rt": leaf_mass * 0.31,
                            "W_fr_harvested": first_measured,
                            "truss_cohorts": _fruit_cohorts(
                                fruit_mass_g_m2=fruit_mass,
                                active_trusses=5,
                                shoots_per_m2=shoots_per_m2,
                            ),
                            "truss_count": 5,
                            "n_f": 4,
                            "reserve_ch2o_g": reserve_pool,
                            "buffer_pool_g": reserve_pool * 0.5,
                        },
                    )
                )
    return candidates


__all__ = [
    "ReconstructionCandidate",
    "build_reconstruction_candidates",
]
