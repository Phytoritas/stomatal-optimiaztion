# TOMICS-HAF 2025-2C Claim Boundary Freeze

Goal 4A freezes the paper-safe claim boundary. The gate result is a correct safeguard result: promotion gate was executed and blocked promotion because compatible cross-dataset evidence is insufficient.

## Allowed Primary Claims

1. TOMICS-HAF was evaluated on the 2025 second cropping cycle as a bounded architecture-discrimination test.
2. Day/night phases were radiation-defined from Dataset1 `env_inside_radiation_wm2`.
3. For 2025-2C, DMC was fixed at `0.056`.
4. Dry yield derived from fresh yield using DMC `0.056` was an estimated dry-yield basis, not direct destructive dry-mass measurement.
5. Latent allocation was observer-supported inference, not direct allocation validation.
6. THORP was used only as a bounded mechanistic prior/correction, not as a raw tomato allocator.
7. Harvest-family evaluation separated allocator family, harvest family, and observation operator.
8. Promotion and cross-dataset gates were executed as safeguards.
9. The gate selected candidates for future cross-dataset testing but did not promote a new shipped TOMICS default.

## Forbidden Claims And Safe Rewrites

| forbidden claim | safe rewrite |
| --- | --- |
| Promotion gate passed. | Promotion gate was executed and blocked promotion because compatible cross-dataset evidence is insufficient. |
| Cross-dataset validation passed. | Cross-dataset gate was executed and blocked because compatible measured datasets are insufficient. |
| Allocation was directly validated. | Latent allocation remains observer-supported inference, not direct allocation validation. |
| Dry yield was directly measured. | Dry yield derived from fresh yield using DMC `0.056` is an estimated dry-yield basis. |
| DMC sensitivity was evaluated. | For 2025-2C, DMC is fixed at `0.056`. |
| Raw THORP allocator was promoted. | THORP was used only as a bounded mechanistic prior/correction, not as a raw tomato allocator. |
| Drought significantly reduced fruit expansion. | Fruit diameter remains sensor-level apparent expansion diagnostics. |
| TOMICS-HAF is universally superior across seasons. | TOMICS-HAF 2025-2C is a bounded architecture-discrimination test. |
| This proves universal multi-season generalization. | TOMICS-HAF 2025-2C is not universal multi-season generalization. |
| A shipped TOMICS default was changed. | No shipped TOMICS default change is recommended at this stage. |

Machine-readable claim boundary outputs:

```text
out/tomics/validation/promotion-gate/haf_2025_2c/claim_boundary_freeze.*
```
