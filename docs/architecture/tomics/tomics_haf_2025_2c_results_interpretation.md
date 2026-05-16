# TOMICS-HAF 2025-2C Results Interpretation

TOMICS-HAF 2025-2C should be interpreted as a bounded architecture-discrimination test on one compatible measured HAF dataset. It is not universal multi-season generalization.

## What The Results Support

- The production observer pipeline produced a 2025-2C feature basis with radiation-defined day/night phases.
- DMC was fixed at `0.056`, and dry yield is an estimated dry-yield basis derived from fresh yield.
- Latent allocation diagnostics support observer-backed inference and guardrail checking.
- Harvest-family outputs support comparing allocator family, harvest family, and observation operator within the 2025-2C evidence boundary.
- Promotion and cross-dataset gates were executed as safeguards.

## What The Gate Decided

Promotion gate was executed and blocked promotion because compatible cross-dataset evidence is insufficient. The measured dataset count is `1`, and the required measured dataset count is `2`.

The best research candidate can be carried forward for future compatible measured datasets. It is not a promoted candidate, and it does not change shipped TOMICS behavior.

## Paper-Safe Interpretation

The result is evidence for architecture discrimination on 2025-2C, not a claim of cross-season superiority. Manuscript language should state the blocked promotion outcome directly and avoid wording that implies direct allocation validation, direct destructive dry-mass measurement, DMC sensitivity analysis, or a shipped default change.
