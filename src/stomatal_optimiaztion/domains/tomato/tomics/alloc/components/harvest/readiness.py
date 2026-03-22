from __future__ import annotations


def _delay_gate(days_since_maturity: float, harvest_delay_days: float) -> bool:
    return float(days_since_maturity) + 1e-9 >= max(float(harvest_delay_days), 0.0)


def ready_tomsim_truss(
    tdvs: float,
    threshold: float = 1.0,
    *,
    days_since_maturity: float = 0.0,
    harvest_delay_days: float = 0.0,
) -> bool:
    return float(tdvs) >= float(threshold) and _delay_gate(days_since_maturity, harvest_delay_days)


def ready_tomgro_ageclass(
    age_class: float,
    mature_class_index: int,
    *,
    mature_pool_residence_days: float = 0.0,
    harvest_delay_days: float = 0.0,
) -> bool:
    return float(age_class) >= float(mature_class_index) and _delay_gate(
        mature_pool_residence_days,
        harvest_delay_days,
    )


def ready_dekoning_fds(
    fds: float,
    threshold: float = 1.0,
    *,
    days_since_maturity: float = 0.0,
    harvest_delay_days: float = 0.0,
) -> bool:
    return float(fds) >= float(threshold) and _delay_gate(days_since_maturity, harvest_delay_days)


def ready_vanthoor_stage(
    stage_index: float,
    n_dev: int,
    *,
    explicit_outflow: float | None = None,
    final_stage_residence_days: float = 0.0,
    harvest_delay_days: float = 0.0,
) -> bool:
    ready_base = float(stage_index) >= float(max(int(n_dev), 1))
    if explicit_outflow is not None and float(explicit_outflow) > 0.0:
        ready_base = True
    return ready_base and _delay_gate(final_stage_residence_days, harvest_delay_days)


__all__ = [
    "ready_dekoning_fds",
    "ready_tomgro_ageclass",
    "ready_tomsim_truss",
    "ready_vanthoor_stage",
]
