from __future__ import annotations

from .test_tomics_harvest_policies import (
    assert_vanthoor_harvest_uses_last_stage_when_no_explicit_outflow_is_supplied,
)


def test_vanthoor_harvest_uses_last_stage_when_no_explicit_outflow_is_supplied() -> None:
    assert_vanthoor_harvest_uses_last_stage_when_no_explicit_outflow_is_supplied()
