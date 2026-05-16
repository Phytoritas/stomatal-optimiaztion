# TOMICS-HAF 2025-2C Limitations

Goal 4A freezes the following limitations for paper, thesis, and PR review use.

- There is one compatible measured HAF dataset: `haf_2025_2c`.
- Promotion requires at least two compatible measured datasets, so promotion remains blocked.
- DMC is fixed at `0.056`; DMC sensitivity was not evaluated for 2025-2C.
- Dry yield derived from fresh yield using DMC `0.056` is estimated dry yield, not direct destructive dry-mass measurement.
- Direct organ partition observations are not available.
- Latent allocation remains observer-supported inference, not direct allocation validation.
- THORP is bounded prior/correction evidence only, not a raw tomato allocator.
- Fruit diameter remains sensor-level apparent expansion diagnostics and must not be used for p-values, allocation calibration, or promotion.
- Budget parity means knob-count and hidden-calibration-budget parity, not wall-clock compute-budget parity.
- Plotkit figure evidence is currently manifest-backed; rendered PNGs remain pending.
- Shipped TOMICS incumbent behavior remains unchanged.

These limitations are not cleanup items to hide. They define the safe claim boundary for this evidence package.
