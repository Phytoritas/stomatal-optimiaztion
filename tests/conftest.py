from __future__ import annotations

import os
import platform
import sys
from pathlib import Path


def _disable_windows_platform_wmi_for_pytest() -> None:
    if sys.platform != "win32":
        return
    if os.environ.get("PHYTORITAS_ALLOW_PLATFORM_WMI", "").strip().lower() in {"1", "true", "yes"}:
        return

    original = getattr(platform, "_wmi_query", None)
    if original is None or getattr(platform, "_phytoritas_wmi_guard", False):
        return

    def _wmi_query_disabled(*_args: object, **_kwargs: object) -> object:
        raise OSError("platform WMI disabled by pytest conftest")

    platform._phytoritas_wmi_guard = True  # type: ignore[attr-defined]
    platform._phytoritas_original_wmi_query = original  # type: ignore[attr-defined]
    platform._wmi_query = _wmi_query_disabled  # type: ignore[assignment]
    if hasattr(platform, "_uname_cache"):
        platform._uname_cache = None  # type: ignore[attr-defined]


_disable_windows_platform_wmi_for_pytest()

SRC_ROOT = Path(__file__).resolve().parents[1] / "src"

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))
