from __future__ import annotations

import pytest

from .test_tomics_knu_harvest_runner_smoke import (
    assert_harvest_family_factorial_runner_writes_required_outputs_from_sanitized_fixture,
)


@pytest.mark.slow
def test_harvest_family_factorial_runner_writes_required_outputs_from_sanitized_fixture(tmp_path) -> None:
    assert_harvest_family_factorial_runner_writes_required_outputs_from_sanitized_fixture(tmp_path)
