from __future__ import annotations

import os
import sys


def _disable_windows_platform_wmi() -> None:
    if sys.platform != "win32":
        return
    if os.environ.get("PHYTORITAS_ALLOW_PLATFORM_WMI", "").strip().lower() in {"1", "true", "yes"}:
        return

    import platform

    original = getattr(platform, "_wmi_query", None)
    if original is None or getattr(platform, "_phytoritas_wmi_guard", False):
        return

    def _wmi_query_disabled(*_args: object, **_kwargs: object) -> object:
        raise OSError("platform WMI disabled by stomatal_optimiaztion package init")

    platform._phytoritas_wmi_guard = True  # type: ignore[attr-defined]
    platform._phytoritas_original_wmi_query = original  # type: ignore[attr-defined]
    platform._wmi_query = _wmi_query_disabled  # type: ignore[assignment]
    if hasattr(platform, "_uname_cache"):
        platform._uname_cache = None  # type: ignore[attr-defined]


_disable_windows_platform_wmi()

__all__ = ["domains"]
