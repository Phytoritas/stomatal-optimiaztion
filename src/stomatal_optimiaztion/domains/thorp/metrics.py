from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray


@dataclass(frozen=True, slots=True)
class BiomassFractionSeries:
    c_l_ts: NDArray[np.floating]
    c_sw_ts: NDArray[np.floating]
    c_hw_ts: NDArray[np.floating]
    c_r_h_by_layer_ts: NDArray[np.floating]
    c_r_v_by_layer_ts: NDArray[np.floating]


@dataclass(frozen=True, slots=True)
class BiomassFractions:
    lmf: NDArray[np.floating]
    smf: NDArray[np.floating]
    rmf: NDArray[np.floating]


@dataclass(frozen=True, slots=True)
class HuberValueSeries:
    c_l_ts: NDArray[np.floating]
    d_ts: NDArray[np.floating]
    d_hw_ts: NDArray[np.floating]


@dataclass(frozen=True, slots=True)
class HuberValueParams:
    sla: float
    xi: float


def biomass_fractions(
    *,
    series: BiomassFractionSeries,
    leaf_c_fraction: float = 0.5,
    wood_c_fraction: float = 0.5,
    root_c_fraction: float = 0.55,
) -> BiomassFractions:
    """Compute THORP-reported biomass fractions from carbon-pool time series.

    Paper-derived conversion (MODEL_CARD:C010 assumption):
      - dry biomass assumed 50% carbon by weight, except roots 55% carbon by weight.
    """

    leaf_biomass = series.c_l_ts / float(leaf_c_fraction)
    wood_biomass = (series.c_sw_ts + series.c_hw_ts) / float(wood_c_fraction)
    root_c = np.sum(series.c_r_h_by_layer_ts + series.c_r_v_by_layer_ts, axis=0)
    root_biomass = root_c / float(root_c_fraction)

    total = leaf_biomass + wood_biomass + root_biomass
    with np.errstate(divide="ignore", invalid="ignore"):
        lmf = leaf_biomass / total
        smf = wood_biomass / total
        rmf = root_biomass / total

    return BiomassFractions(
        lmf=lmf.astype(float),
        smf=smf.astype(float),
        rmf=rmf.astype(float),
    )


def huber_value(
    *,
    series: HuberValueSeries,
    params: HuberValueParams,
) -> NDArray[np.floating]:
    """Compute the sapwood-to-leaf area ratio from migrated THORP time series."""

    leaf_area = float(params.sla) * series.c_l_ts
    sapwood_area = float(params.xi) * (series.d_ts**2 - series.d_hw_ts**2)
    with np.errstate(divide="ignore", invalid="ignore"):
        hv = sapwood_area / leaf_area
    return hv.astype(float)
