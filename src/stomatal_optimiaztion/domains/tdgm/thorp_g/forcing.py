from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
from netCDF4 import Dataset
from numpy.typing import NDArray

from stomatal_optimiaztion.domains.tdgm.thorp_g.config import ThorpGParams


@dataclass(frozen=True, slots=True)
class Forcing:
    t: NDArray[np.floating]
    t_a: NDArray[np.floating]
    t_soil: NDArray[np.floating]
    rh: NDArray[np.floating]
    precip: NDArray[np.floating]
    u10: NDArray[np.floating]
    r_incom: NDArray[np.floating]
    z_a: NDArray[np.floating]

    @property
    def t_end(self) -> float:
        return float(self.t[-1])


def load_forcing(params: ThorpGParams) -> Forcing:
    """Load forcing time series following MATLAB `INPUTS_2_Environmental_Conditions.m`."""

    path = Path(params.forcing_path)
    if not path.exists():
        raise FileNotFoundError(f"Forcing netCDF file not found: {path}")

    with Dataset(path) as ds:
        raw = np.asarray(ds.variables["data"][:], dtype=float)

    if raw.ndim != 2:
        raise ValueError(f"Unexpected forcing shape: {raw.shape}")
    if raw.shape[1] == 6 and raw.shape[0] != 6:
        pass
    elif raw.shape[0] == 6 and raw.shape[1] != 6:
        raw = raw.T
    else:
        raise ValueError(f"Expected forcing with 6 variables, got shape {raw.shape}")

    t_a = raw[:, 0].astype(float)
    t_soil = raw[:, 1].astype(float)
    precip = raw[:, 2].astype(float)
    rh = raw[:, 3].astype(float)
    r_incom = raw[:, 4].astype(float)
    u10 = raw[:, 5].astype(float)

    rh = np.clip(rh, 0.0, 1.0)

    n_10yr = 10 * 365 * 4
    t_a = t_a[:n_10yr]
    t_soil = t_soil[:n_10yr]
    precip = precip[:n_10yr]
    rh = rh[:n_10yr]
    r_incom = r_incom[:n_10yr]
    u10 = u10[:n_10yr]

    q = int(params.forcing_repeat_q)
    t_a = np.tile(t_a, q)
    t_soil = np.tile(t_soil, q)
    precip = np.tile(precip, q)
    rh = np.tile(rh, q)
    r_incom = np.tile(r_incom, q)
    u10 = np.tile(u10, q)

    n_dt = t_a.size
    t_bgn = 0.0
    t_end = t_bgn + (n_dt - 1) * params.dt
    t = np.arange(t_bgn, t_end + params.dt, params.dt, dtype=float)

    day = t / (24 * 3600.0) - 365.0 * np.floor(t / (365.0 * 24.0 * 3600.0))
    hour = (t + params.dt / 2) / 3600.0 - 24.0 * np.floor(t / (24.0 * 3600.0))
    lat = float(params.forcing_lat_rad)
    dec = -23.44 * np.pi / 180.0 * np.cos(2 * np.pi / 365.0 * (day + 10))
    lha = 15.0 * np.pi / 180.0 * (hour - 12.0)
    z_a = np.arccos(np.sin(lat) * np.sin(dec) + np.cos(lat) * np.cos(dec) * np.cos(lha))
    z_a = np.pi / 2 - z_a

    precip = precip * float(params.forcing_precip_scale)
    rh = rh * float(params.forcing_rh_scale)

    return Forcing(
        t=t,
        t_a=t_a,
        t_soil=t_soil,
        rh=rh,
        precip=precip,
        u10=u10,
        r_incom=r_incom,
        z_a=z_a,
    )
