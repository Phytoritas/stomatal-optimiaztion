from __future__ import annotations

import pytest

from .test_tomics_knu_harvest_runner_smoke import (
    assert_harvest_promotion_gate_runner_writes_scorecard_outputs_from_sanitized_fixture,
)


@pytest.mark.slow
def test_harvest_promotion_gate_runner_writes_scorecard_outputs_from_sanitized_fixture(tmp_path, monkeypatch) -> None:
    assert_harvest_promotion_gate_runner_writes_scorecard_outputs_from_sanitized_fixture(tmp_path, monkeypatch)
