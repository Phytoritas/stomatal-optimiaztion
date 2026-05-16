# HAF 2025-2C Harvest Budget Parity

Goal 3B writes a budget-parity audit for staged harvest-family evaluation. The
audit is a prerequisite output only; it is not a final promotion gate.

Budget accounting includes:

- harvest-family knobs;
- leaf-harvest knobs;
- the DMC `0.056` observation-operator knob;
- latent allocation prior-family knobs;
- extra calibration budget flags.

The budget-parity basis is `knob_count_and_hidden_calibration_budget`.
This means Goal 3B controls the number of harvest, observation-operator,
latent-prior, and hidden-calibration knobs exposed to each candidate. It does
not evaluate wall-clock compute-budget parity.

The harvest-family metadata must retain:

- `budget_parity_basis = "knob_count_and_hidden_calibration_budget"`
- `wall_clock_compute_budget_parity_evaluated = false`
- `wall_clock_compute_budget_parity_required_for_goal_3b = false`
- `budget_parity_limitations` explaining that parity is not wall-clock parity

No candidate may be considered ready for promotion in Goal 3B. Output metadata
must retain:

- `promotion_gate_run = false`
- `single_dataset_promotion_allowed = false`
- `cross_dataset_gate_run = false`
- `shipped_TOMICS_incumbent_changed = false`

Latent allocation remains observer-supported inference, not direct allocation
validation.
