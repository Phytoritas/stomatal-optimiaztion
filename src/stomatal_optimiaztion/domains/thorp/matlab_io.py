from __future__ import annotations

from pathlib import Path
from typing import Any

from scipy.io import loadmat, savemat


def load_mat(path: str | Path) -> dict[str, Any]:
    """Load a legacy THORP MAT file with the same scipy options as the source repo."""

    mat_path = Path(path)
    if not mat_path.exists():
        raise FileNotFoundError(mat_path)
    return loadmat(mat_path, squeeze_me=True, struct_as_record=False)


def save_mat(path: str | Path, data: dict[str, Any]) -> None:
    """Persist a legacy THORP MAT payload, creating parent directories as needed."""

    mat_path = Path(path)
    mat_path.parent.mkdir(parents=True, exist_ok=True)
    savemat(mat_path, data, do_compression=True)
