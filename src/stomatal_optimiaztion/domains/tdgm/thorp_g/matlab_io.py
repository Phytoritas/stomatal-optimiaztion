from __future__ import annotations

from pathlib import Path
from typing import Any

from scipy.io import loadmat, savemat


def load_mat(path: str | Path) -> dict[str, Any]:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(p)
    return loadmat(p, squeeze_me=True, struct_as_record=False)


def save_mat(path: str | Path, data: dict[str, Any]) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    savemat(p, data, do_compression=True)

