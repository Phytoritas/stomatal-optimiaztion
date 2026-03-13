from __future__ import annotations

from pathlib import Path

from stomatal_optimiaztion.domains.thorp.forcing import Forcing
from stomatal_optimiaztion.domains.thorp.params import THORPParams
from stomatal_optimiaztion.domains.thorp.simulation import SimulationOutputs
from stomatal_optimiaztion.domains.thorp.simulation import run as _baseline_run


def run(
    params: THORPParams | None = None,
    *,
    forcing: Forcing | None = None,
    max_steps: int | None = None,
    save_mat_path: str | Path | None = None,
) -> SimulationOutputs:
    """Run THORP simulation through the stable refactor-friendly wrapper surface."""

    return _baseline_run(
        params=params,
        forcing=forcing,
        max_steps=max_steps,
        save_mat_path=save_mat_path,
    )
