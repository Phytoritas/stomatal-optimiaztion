from __future__ import annotations

import os
import platform
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest


@pytest.mark.skipif(sys.platform != "win32", reason="Windows-specific startup guard")
def test_windows_platform_wmi_guard_is_active_in_test_process() -> None:
    if os.environ.get("PHYTORITAS_ALLOW_PLATFORM_WMI", "").strip().lower() in {"1", "true", "yes"}:
        pytest.skip("Repo-local platform WMI guard explicitly disabled")

    assert getattr(platform, "_phytoritas_wmi_guard", False) is True
    with pytest.raises(OSError, match="disabled by"):
        platform._wmi_query("CPU", "Architecture")  # type: ignore[attr-defined]


@pytest.mark.skipif(sys.platform != "win32", reason="Windows-specific startup guard")
def test_windows_platform_wmi_guard_preserves_fast_platform_machine_fallback() -> None:
    machine = platform.machine()
    assert isinstance(machine, str)


@pytest.mark.skipif(sys.platform != "win32", reason="Windows-specific startup guard")
def test_repo_package_import_guard_allows_pandas_backed_validation_import() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    probe_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".py",
            dir=repo_root,
            delete=False,
            encoding="utf-8",
        ) as handle:
            handle.write(
                "from pathlib import Path\n"
                "import sys\n"
                "repo_root = Path(__file__).resolve().parent\n"
                "sys.path.insert(0, str(repo_root / 'src'))\n"
                "from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.cross_dataset_gate import (\n"
                "    cross_dataset_proxy_guardrail,\n"
                ")\n"
                "print(cross_dataset_proxy_guardrail.__name__)\n"
            )
            probe_path = Path(handle.name)
        completed = subprocess.run(
            [sys.executable, str(probe_path)],
            cwd=repo_root,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
    finally:
        if probe_path is not None and probe_path.exists():
            probe_path.unlink()
    assert completed.returncode == 0, completed.stderr
    assert completed.stdout.strip()
