# Decision Register

Use this file for local operating decisions that are not yet mature enough to become ADRs.

Append dated entries instead of replacing history.

## 2026-05-16 TOMICS-HAF Pipeline Contract Intake

- `artifacts/TOMICS_Architecture_Pipeline.md` is the active architecture contract for the TOMICS-HAF 2025_2C pipeline.
- TOMICS-HAF remains tomato-first: fruit-vs-vegetative partition uses tomato source-sink / sink-strength logic, not raw THORP.
- THORP-derived terms may be used only as bounded, regularized latent-allocation priors, bounded root/hydraulic corrections, or diagnostic comparators.
- Shipped `partition_policy: tomics` remains the incumbent unless a formal promotion gate passes.
- Dataset1 radiation is the primary basis for final day/night when directly usable; fixed 06:00-18:00 windows are compatibility-only.
- Fruit diameter remains sensor-level apparent expansion diagnostics only; no p-values, treatment endpoint, allocation calibration, or promotion basis.
- Allocator families, harvest families, and observation operators remain separate axes for validation and promotion review.
- Latent allocation inference is not direct allocation validation unless organ partitioning observations exist.

## 2026-05-16 TOMICS-HAF Goal 2 Observer Pipeline

- Goal 2 implements a thin TOMICS-HAF observer/profile layer around existing TOMICS machinery without changing shipped `partition_policy: tomics`.
- Day/night phases are radiation-defined from Dataset1 `env_inside_radiation_wm2`; fixed `06:00-18:00` windows are compatibility-only.
- raw `.dat` `SolarRad_Avg` remains fallback-only for 2025-2C because Dataset1 radiation is directly usable.
- Fruit diameter remains sensor-level apparent expansion diagnostics only and is not a treatment endpoint, p-value source, allocation calibration target, or promotion target.
- Goal 2 observer feature frame is an input scaffold for later latent allocation inference, not direct allocation validation.

## 2026-05-16 TOMICS-HAF Goal 2.5 Production Observer Export

- Goal 2.5 adds production chunk aggregation for full Dataset1 and Dataset2 observer export without full in-memory materialization.
- Production export processed Dataset1 `139713462/139713462` rows and Dataset2 `46571154/46571154` rows with `row_cap_applied=false`.
- Production metadata reports `production_export_completed=true` and `production_ready_for_latent_allocation=true`.
- Event-bridged ET remains `uncalibrated_no_daily_total` because existing daily event-bridged totals were not available.
- Latent allocation inference, harvest-family factorials, cross-dataset gates, and promotion gates remain unrun.
