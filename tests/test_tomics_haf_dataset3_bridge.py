import pandas as pd

from stomatal_optimiaztion.domains.tomato.tomics.observers.dataset3_bridge import (
    build_dataset3_growth_phenology_bridge,
)


def test_dataset3_mapping_confidence_modes() -> None:
    direct, meta = build_dataset3_growth_phenology_bridge(
        pd.DataFrame({"date": ["2025-12-14"], "loadcell_id": [1], "treatment": ["Control"], "stem_diameter": [9.0]})
    )
    no_date, no_date_meta = build_dataset3_growth_phenology_bridge(
        pd.DataFrame({"loadcell_id": [1], "treatment": ["Control"], "stem_diameter": [9.0]})
    )
    treatment_only, treatment_meta = build_dataset3_growth_phenology_bridge(
        pd.DataFrame({"date": ["2025-12-14"], "treatment": ["Control"], "stem_diameter": [9.0]})
    )
    unlinked, unlinked_meta = build_dataset3_growth_phenology_bridge(pd.DataFrame({"stem_diameter": [9.0]}))

    assert meta["Dataset3_mapping_confidence"] == "direct_loadcell"
    assert no_date_meta["Dataset3_mapping_confidence"] == "direct_loadcell_no_date"
    assert treatment_meta["Dataset3_mapping_confidence"] == "treatment_level_only"
    assert unlinked_meta["Dataset3_mapping_confidence"] == "unlinked"
    assert direct["causal_allocation_fitting_run"].eq(False).all()
    assert no_date["allocation_use"].eq("growth_phenology_observer_only").all()
    assert treatment_only.shape[0] == 1
    assert unlinked.shape[0] == 1

