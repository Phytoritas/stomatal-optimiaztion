"""Legacy THORP grouped I/O namespace."""

from __future__ import annotations

from stomatal_optimiaztion.domains.thorp.forcing import Forcing, load_forcing
from stomatal_optimiaztion.domains.thorp.matlab_io import load_mat, save_mat

__all__ = ["Forcing", "load_forcing", "load_mat", "save_mat"]
