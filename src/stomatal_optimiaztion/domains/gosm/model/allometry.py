from __future__ import annotations

import numpy as np

from stomatal_optimiaztion.domains.gosm.utils.traceability import implements


@implements("Eq.S3.LAI")
def leaf_area_index(*, la: float | np.ndarray, phi_l: float, w: float) -> np.ndarray:
    """Leaf area index from canopy leaf area, crown width, and projection ratio."""

    la = np.asarray(la, dtype=float)
    return la / float(phi_l) / float(w) ** 2
