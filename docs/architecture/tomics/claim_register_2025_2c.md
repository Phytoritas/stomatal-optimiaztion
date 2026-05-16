# TOMICS-HAF 2025-2C Claim Register

Goal 3C emits a paper-safe claim register under:

```text
out/tomics/validation/promotion-gate/haf_2025_2c/claim_register.{csv,md,json}
```

The register separates allowed, conditional, and forbidden claims. The current safe language is bounded:

- We evaluated TOMICS-HAF on the 2025 second cropping cycle as a bounded architecture-discrimination test.
- For 2025-2C, DMC was fixed at `0.056`.
- Dry yield derived from fresh yield using DMC `0.056` was an estimated dry-yield basis, not direct destructive dry-mass measurement.
- Latent allocation was observer-supported inference, not direct allocation validation.
- THORP was used only as a bounded mechanistic prior/correction, not as a raw tomato allocator.
- The 2025-2C gate selected candidates for future cross-dataset testing but did not promote a new shipped TOMICS default when the gate blocked promotion.

Forbidden claims include direct allocation validation, direct dry-yield measurement, DMC sensitivity evaluation, raw THORP promotion, drought significance claims from fruit diameter, and universal multi-season generalization.
