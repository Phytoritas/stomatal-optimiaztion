from __future__ import annotations

import math

from stomatal_optimiaztion.domains.tomato.tomics.alloc.components.harvest import (
    run_harvest_step,
)
from stomatal_optimiaztion.domains.tomato.tomics.alloc.components.harvest.fruit_harvest_tomsim import (
    TomsimTrussHarvestPolicy,
)
from stomatal_optimiaztion.domains.tomato.tomics.alloc.components.harvest.leaf_harvest import (
    LinkedTrussStageLeafHarvestPolicy,
)
from stomatal_optimiaztion.domains.tomato.tomics.alloc.validation.harvest_family_eval import (
    _apply_harvest_update_to_model,
    _post_writeback_audit,
)

from .test_tomics_harvest_zero_yield import _mature_state


def test_post_writeback_audit_reports_zero_dropped_nonharvested_mass_after_delayed_pick() -> None:
    adapter, _row, state = _mature_state(tdvs=1.0, fruit_mass=5.0)
    delayed_pick = run_harvest_step(
        fruit_policy=TomsimTrussHarvestPolicy(tdvs_harvest_threshold=1.2),
        leaf_policy=LinkedTrussStageLeafHarvestPolicy(),
        state=state,
        env={},
        dt_days=1.0,
    )

    _apply_harvest_update_to_model(adapter=adapter, update=delayed_pick.final_update)
    audit = _post_writeback_audit(
        state=delayed_pick.final_update.updated_state,
        adapter=adapter,
        harvested_flux_g_m2_d=float(delayed_pick.final_update.fruit_harvest_flux_g_m2_d),
        mature_streak_days=1.0,
    )

    assert math.isclose(float(audit["pre_writeback_total_system_fruit_g_m2"]), 5.0)
    assert math.isclose(float(audit["post_writeback_total_system_fruit_g_m2"]), 5.0)
    assert math.isclose(float(audit["post_writeback_dropped_nonharvested_mass_g_m2"]), 0.0)
    assert math.isclose(float(audit["mature_onplant_mass_g_m2"]), 5.0)
    assert bool(audit["all_zero_harvest_series"]) is True
