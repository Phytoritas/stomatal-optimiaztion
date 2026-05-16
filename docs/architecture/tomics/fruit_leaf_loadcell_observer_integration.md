# TOMICS-HAF 2025-2C Fruit/Leaf Loadcell Observer Integration

The fruit and leaf raw `.dat` sensors are integrated as observer diagnostics around existing TOMICS machinery.

Confirmed leaf-temperature mapping:

- `LeafTemp1_Avg` maps to loadcell `4`, treatment `Drought`.
- `LeafTemp2_Avg` maps to loadcell `1`, treatment `Control`.

Provisional fruit-diameter mapping:

- `Fruit1Diameter_Avg` maps provisionally to loadcell `4`, treatment `Drought`.
- `Fruit2Diameter_Avg` maps provisionally to loadcell `1`, treatment `Control`.

Fruit diameter is sensor-level apparent expansion diagnostics only. It may be used as a descriptive observer, posterior diagnostic, or hydraulic-realization readout.

Fruit diameter must not be used for treatment p-values, allocation calibration, hydraulic gate calibration, model promotion, or harvest-family promotion targets.

The observer layer writes radiation-phase and fixed-clock compatibility summaries, but day/night phases for downstream observer features are radiation-defined from Dataset1 `env_inside_radiation_wm2`.
