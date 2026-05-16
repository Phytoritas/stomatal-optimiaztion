# TOMICS-HAF 2025-2C Radiation-Defined Day/Night Contract

Dataset1 radiation defines day/night phases for the TOMICS-HAF 2025-2C observer layer.

- Primary source: Dataset1.
- Primary column: `env_inside_radiation_wm2`.
- Main threshold: `0 W m-2`.
- Sensitivity thresholds: `0`, `1`, `5`, and `10 W m-2`.
- Main day: `env_inside_radiation_wm2 > 0`.
- Main night: `env_inside_radiation_wm2 == 0`.

Fixed `06:00-18:00` windows are not primary. They are compatibility-only outputs for legacy comparison and sensor-QC bookkeeping.

The raw `.dat` `SolarRad_Avg` column is verified as a fallback candidate for this dataset, but Goal 1 established that Dataset1 radiation is high-frequency and directly usable. Therefore `SolarRad_Avg` remains fallback-only for the 2025-2C observer run.

This contract does not change shipped TOMICS defaults and does not promote any allocator.
