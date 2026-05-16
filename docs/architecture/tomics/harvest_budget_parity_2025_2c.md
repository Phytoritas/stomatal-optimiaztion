# HAF 2025-2C Harvest Budget Parity

Goal 3B writes a budget-parity audit for staged harvest-family evaluation. The
audit is a prerequisite output only; it is not a final promotion gate.

Budget accounting includes:

- harvest-family knobs;
- leaf-harvest knobs;
- the DMC `0.056` observation-operator knob;
- latent allocation prior-family knobs;
- extra calibration budget flags.

No candidate may be considered ready for promotion in Goal 3B. Output metadata
must retain:

- `promotion_gate_run = false`
- `single_dataset_promotion_allowed = false`
- `cross_dataset_gate_run = false`
- `shipped_TOMICS_incumbent_changed = false`

Latent allocation remains observer-supported inference, not direct allocation
validation.
