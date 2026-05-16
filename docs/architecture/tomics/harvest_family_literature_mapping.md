# TOMICS-HAF Harvest-Family Literature Mapping

This document records the Goal 3B implementation mapping only. It is not a
claim that harvest-family evaluation is complete across seasons.

Mapped harvest-family labels:

- `tomsim_truss_incumbent`: shipped TOMICS/TOMSIM-style incumbent truss harvest.
- `tomgro_ageclass_mature_pool`: TOMGRO-style age-class mature-pool research family.
- `dekoning_fds_ripe`: De Koning fruit-development-stage ripe-family research family.
- `vanthoor_boxcar_stageflow`: Vanthoor-style boxcar stage-flow research family.

Mapped leaf-harvest labels:

- `leaf_harvest_tomsim_legacy`
- `leaf_harvest_none`
- `leaf_harvest_max_lai`
- `leaf_harvest_vanthoor_mcleafhar`

For 2025-2C, DMC is fixed at `0.056`. Dry yield derived from fresh yield using
DMC `0.056` is an estimated dry-yield basis, not direct destructive dry-mass
measurement. DMC sensitivity is disabled unless explicitly re-enabled later.

Latent allocation remains observer-supported inference, not direct allocation
validation. THORP is used only as a bounded mechanistic prior/correction, not as
a raw tomato allocator.
