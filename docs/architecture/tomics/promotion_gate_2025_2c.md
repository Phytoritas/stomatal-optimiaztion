# TOMICS-HAF 2025-2C Promotion Gate

Goal 3C executes the HAF 2025-2C promotion gate as a safeguard. Gate execution is not the same as gate passage.

The gate preserves the 2025-2C contracts:

- DMC is fixed at `0.056`.
- DMC sensitivity is disabled.
- Dry yield derived from fresh yield using DMC `0.056` is an estimated dry-yield basis, not direct destructive dry-mass measurement.
- Latent allocation remains observer-supported inference, not direct allocation validation.
- THORP is used only as a bounded mechanistic prior/correction, not as a raw tomato allocator.
- Fruit diameter remains sensor-level apparent expansion diagnostics.
- Shipped TOMICS incumbent remains unchanged.

Promotion requires at least two compatible measured datasets and a passing cross-dataset gate. With only `haf_2025_2c` available, promotion is blocked by `cross_dataset_evidence_insufficient`.

Primary command:

```powershell
poetry run python scripts/run_tomics_haf_promotion_gate.py --config configs/exp/tomics_haf_2025_2c_promotion_gate.yaml
```

Primary private outputs are written under:

```text
out/tomics/validation/promotion-gate/haf_2025_2c/
```
