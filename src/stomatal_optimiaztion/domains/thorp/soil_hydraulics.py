from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

from stomatal_optimiaztion.domains.thorp.implements import implements


@dataclass(frozen=True, slots=True)
class SoilHydraulics:
    """THORP soil hydraulic relationships used by the soil column and roots."""

    n_vg: float
    alpha_vg: float
    l_vg: float
    e_z_n: float
    e_z_k_s_sat: float
    vwc_res: float = 0.0

    @implements("E_S2_8")
    def vwc_sat(self, z: NDArray[np.floating]) -> NDArray[np.floating]:
        return 0.4 * np.exp(-z / self.e_z_n)

    @implements("E_S2_7")
    def k_s_sat(self, z: NDArray[np.floating]) -> NDArray[np.floating]:
        return 6e-7 * np.exp(-z / self.e_z_k_s_sat)

    def k_soil_sat(self, z: NDArray[np.floating]) -> NDArray[np.floating]:
        return self.k_s_sat(z)

    @implements("E_S2_6")
    def s_e(self, psi_soil: NDArray[np.floating]) -> NDArray[np.floating]:
        return (1 + np.abs(self.alpha_vg * psi_soil) ** self.n_vg) ** -(1 - 1 / self.n_vg)

    @implements("E_S2_5")
    def vwc(
        self, psi_soil: NDArray[np.floating], z: NDArray[np.floating]
    ) -> NDArray[np.floating]:
        return self.vwc_res + (self.vwc_sat(z) - self.vwc_res) * self.s_e(psi_soil)

    @implements("E_S2_4")
    def k_s(
        self, psi_soil: NDArray[np.floating], z: NDArray[np.floating]
    ) -> NDArray[np.floating]:
        s_e = self.s_e(psi_soil)
        term = (1 - (1 - s_e ** (1 / (1 - 1 / self.n_vg))) ** (1 - 1 / self.n_vg)) ** 2
        return self.k_s_sat(z) * s_e**self.l_vg * term

    def k_soil(
        self, psi_soil_by_layer: NDArray[np.floating], z: NDArray[np.floating]
    ) -> NDArray[np.floating]:
        return self.k_s(psi_soil_by_layer, z)
