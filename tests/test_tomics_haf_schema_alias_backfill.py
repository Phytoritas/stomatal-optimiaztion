from stomatal_optimiaztion.domains.tomato.tomics.observers.input_schema_audit import match_semantic_roles


def test_actual_observer_columns_are_mapped_to_semantic_roles() -> None:
    matched = match_semantic_roles(
        [
            "moisture_percent",
            "ec_ds",
            "tensiometer_hp",
            "flower_cluster_no",
            "loadcell_daily_yield_g",
            "final_dry_yield_g_est_5p6pct",
            "loadcell_daily_dry_yield_g_est_default_5p6pct",
        ]
    )

    assert matched["moisture"] == ["moisture_percent"]
    assert matched["ec"] == ["ec_ds"]
    assert matched["tensiometer"] == ["tensiometer_hp"]
    assert matched["truss_position"] == ["flower_cluster_no"]
    assert "loadcell_daily_yield_g" in matched["yield_fresh"]
    assert "final_dry_yield_g_est_5p6pct" in matched["estimated_dry_yield_from_dmc"]
    assert "loadcell_daily_dry_yield_g_est_default_5p6pct" in matched["estimated_dry_yield_from_dmc"]
    assert "direct_dry_yield_measured" not in matched


def test_measured_and_dmc_estimated_dry_yield_aliases_are_distinct() -> None:
    matched = match_semantic_roles(["yield_dry_g", "final_dry_yield_g_est_5p6pct"])

    assert matched["direct_dry_yield_measured"] == ["yield_dry_g"]
    assert matched["estimated_dry_yield_from_dmc"] == ["final_dry_yield_g_est_5p6pct"]
