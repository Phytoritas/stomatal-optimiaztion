from __future__ import annotations

import numpy as np
from scipy import special


def polylog2(z: np.ndarray | float) -> np.ndarray:
    """Vectorized Li_2(z) using SciPy's Spence function."""

    return special.spence(1 - np.asarray(z))
