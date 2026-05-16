from stomatal_optimiaztion.domains.tomato.tomics.observers.sensor_mapping import (
    fruit_diameter_policy_metadata,
    load_sensor_mapping,
)


def test_2025_2c_sensor_mapping_contract() -> None:
    mapping = load_sensor_mapping()

    assert mapping["leaf_sensor_map"]["LeafTemp1_Avg"]["loadcell_id"] == 4
    assert mapping["leaf_sensor_map"]["LeafTemp1_Avg"]["treatment"] == "Drought"
    assert mapping["leaf_sensor_map"]["LeafTemp2_Avg"]["loadcell_id"] == 1
    assert mapping["leaf_sensor_map"]["LeafTemp2_Avg"]["treatment"] == "Control"
    assert mapping["fruit_sensor_map"]["Fruit1Diameter_Avg"]["mapping_status"] == "provisional"
    assert mapping["fruit_sensor_map"]["Fruit2Diameter_Avg"]["loadcell_id"] == 1

    policy = fruit_diameter_policy_metadata(mapping)
    assert policy["fruit_diameter_p_values_allowed"] is False
    assert policy["fruit_diameter_allocation_calibration_target"] is False

