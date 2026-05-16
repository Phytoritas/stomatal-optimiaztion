# Observer Metadata Contract

TOMICS-HAF observer metadata is written with stable top-level canonical keys and no case-insensitive duplicates. This avoids PowerShell-style collisions such as `LAI_available` versus `lai_available` and `VPD_available` versus `vpd_available`.

Canonical top-level keys include:

- `LAI_available`
- `VPD_available`
- `Dataset3_mapping_confidence`
- `fruit_diameter_p_values_allowed`
- `fruit_diameter_allocation_calibration_target`
- `fruit_diameter_model_promotion_target`
- `shipped_TOMICS_incumbent_changed`

Legacy or superseded keys may be retained only under `legacy_metadata`. Stage snapshots are written separately for schema/radiation, observer, and production observer stages so one stage does not silently overwrite another.
