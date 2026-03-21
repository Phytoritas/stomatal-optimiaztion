from __future__ import annotations


def ready_tomsim_truss(tdvs: float, threshold: float = 1.0) -> bool:
    return float(tdvs) >= float(threshold)


def ready_tomgro_ageclass(age_class: float, mature_class_index: int) -> bool:
    return float(age_class) >= float(mature_class_index)


def ready_dekoning_fds(fds: float, threshold: float = 1.0) -> bool:
    return float(fds) >= float(threshold)


def ready_vanthoor_stage(
    stage_index: float,
    n_dev: int,
    explicit_outflow: float | None = None,
) -> bool:
    if explicit_outflow is not None and float(explicit_outflow) > 0.0:
        return True
    return float(stage_index) >= float(max(int(n_dev), 1))


__all__ = [
    "ready_dekoning_fds",
    "ready_tomgro_ageclass",
    "ready_tomsim_truss",
    "ready_vanthoor_stage",
]
