# TOMICS A1-A4 Allocation Factorial Selection

Issue: #302

## Executive summary

This review completes the gated A1-A4 TOMICS allocation architecture framing without changing shipped runtime behavior.
The current shipped `partition_policy: tomics` path remains the incumbent and is mapped here as A3.
A4 exists as runnable opt-in research code behind `tomics_promoted_research`, but it is not promotion-ready on the current measured-yield evidence.
A1 stays the tomato biological baseline, and A2 stays the raw THORP-like negative control.

Recommendation: keep A3 as shipped incumbent, keep A4 research-only, reject A2 for promotion, and use A1 only as the biological baseline.

## Why the earlier three-way framing was incomplete

The prior allocation comparison usually grouped the surface as legacy, current, and promoted.
That framing was useful for KNU current-vs-promoted review, but it was incomplete for a promotion decision because the raw THORP-like direct allocation failure mode was not a first-class architecture ID.
It also risked conflating allocation architecture with harvest-family/yield semantics.
This review separates the four allocation candidates from TOMSIM/TOMGRO/De Koning/Vanthoor/Kuijpers harvest-family context.

## Correct A1A4 allocation architecture definitions

| ID | Architecture ID | Repo lane alias | Runtime policy | Role |
|---|---|---|---|---|
| A1 | `legacy_sink_baseline` | `legacy_sink_baseline` | `legacy` | Biological tomato sink baseline |
| A2 | `raw_thorp_direct_negative_control` | `raw_reference_thorp` | `thorp_fruit_veg` | Negative control |
| A3 | `shipped_tomics_bounded_incumbent` | `incumbent_current` | `tomics` | Shipped incumbent |
| A4 | `research_promoted_marginal_allocator` | `research_promoted` | `tomics_promoted_research` | Research-only candidate |

The lane registry also contains `research_current` for the previously selected current research architecture, but it is not the missing fourth architecture in this A1-A4 framing.

## Code/doc surfaces inspected

Code surfaces:

- `src/stomatal_optimiaztion/domains/tomato/tomics/alloc/components/partitioning/policy.py`
- `src/stomatal_optimiaztion/domains/tomato/tomics/alloc/components/partitioning/sink_based.py`
- `src/stomatal_optimiaztion/domains/tomato/tomics/alloc/components/partitioning/thorp_policies.py`
- `src/stomatal_optimiaztion/domains/tomato/tomics/alloc/components/partitioning/tomics_policy.py`
- `src/stomatal_optimiaztion/domains/tomato/tomics/alloc/components/partitioning/promoted_policy.py`
- `src/stomatal_optimiaztion/domains/tomato/tomics/alloc/components/partitioning/promoted_modes.py`
- `src/stomatal_optimiaztion/domains/tomato/tomics/alloc/models/tomato_legacy/tomato_model.py`
- `src/stomatal_optimiaztion/domains/tomato/tomics/alloc/validation/current_vs_promoted.py`
- `src/stomatal_optimiaztion/domains/tomato/tomics/alloc/validation/lane_matrix/allocation_lane_registry.py`
- `src/stomatal_optimiaztion/domains/tomato/tomics/alloc/validation/lane_matrix/lane_gate.py`
- `src/stomatal_optimiaztion/domains/tomato/tomics/alloc/validation/datasets/`

Docs/configs:

- `README.md`
- `docs/variable_glossary.md`
- `docs/legacy_name_mapping.md`
- `docs/architecture/tomics-allocation-architecture-pipeline.md`
- `docs/architecture/tomics-current-vs-promoted-factorial-knu.md`
- `docs/architecture/tomics-lane-matrix-architecture.md`
- `docs/architecture/tomics-harvest-architecture-pipeline.md`
- `docs/architecture/system/current_architecture_map.md`
- `docs/architecture/review/tomics-promoted-allocator-design.md`
- `docs/architecture/review/tomics-harvest-family-review.md`
- `docs/architecture/review/tomics-harvest-family-gap-analysis.md`
- `docs/architecture/review/tomics-harvest-equation-manifest.md`
- `configs/exp/tomics_allocation_factorial.yaml`
- `configs/exp/tomics_current_vs_promoted_factorial_knu.yaml`
- `configs/exp/tomics_lane_matrix.yaml`
- `configs/exp/tomics_lane_matrix_gate.yaml`
- `configs/exp/tomics_multidataset_harvest_factorial_mixed_measured.yaml`
- `configs/data/tomics_multidataset_candidates/traitenv_candidate_registry.json`

## Dataset availability and caveats

| Dataset | Role | Status | Runtime evidence | Caveat |
|---|---|---|---|---|
| `knu_actual` | Primary promotion evidence | RUNNABLE smoke fixture; longrun config present | `tests/fixtures/knu_sanitized/` has 16 forcing rows and 4 harvest rows | Longrun KNU xlsx path in `configs/exp/tomics_lane_matrix.yaml` is absent in this checkout |
| `public_rda__yield` | Secondary robustness / directionality | RUNNABLE review-only derived-DW | `data/fixtures/public_rda_sanitized/2018_farm10_season1_ripe_tomato/` has 5,952 forcing rows and 25 harvest rows | Measured fresh shipment mass converted to DW with 0.065 dry-matter fraction |
| `public_ai_competition__yield` | Smoke / directionality | RUNNABLE review-only derived-DW | `data/fixtures/public_ai_competition_sanitized/2023_farmKRKW000001_season_na_tomato/` has 192 forcing rows and 2 harvest rows | Fresh harvest proxy converted to DW with 0.065 dry-matter fraction and `plants_per_m2 = 2.86` |
| `knu_rootzone_sanitized` | Optional root-zone context | Available | 35,496 aligned root-zone rows and 35,496 aligned EC rows | Not an observed harvest target |
| `school_trait_bundle__yield` | Excluded | `DRAFT_NEEDS_RAW_FIXTURE` | No runnable fixture/mapping | Must not enter runtime evaluation yet |

The public RDA and public AI lanes are not direct measured fruit dry-weight datasets.
They remain `review_only_derived_dw` evidence and cannot be the sole basis for promotion.

## Factorial design actually used

Stage 0 surface audit:
the lane registry isolates A1, A2, A3, and A4 without changing shipped defaults.
A4 is present in runnable code and config as `tomics_promoted_research`, not docs-only.

Stage 1 four-way allocation matrix:
the repo has a lane-matrix config that includes `legacy_sink_baseline`, `incumbent_current`, `research_promoted`, and `raw_reference_thorp`.
The full default lane-matrix command was not rerun because the configured longrun KNU `data/forcing/tomato_validation_data_yield_260321.xlsx` is absent in this checkout.
Instead, this review uses existing KNU current-vs-promoted artifacts that already include legacy, raw THORP-like, shipped TOMICS, and promoted-selected rows.

Stage 2 A3/A4 focused comparison:
existing KNU artifacts under `out/tomics/validation/knu/architecture/` were used for the measured-yield comparison.
The selected current research architecture is `kuijpers_hybrid_candidate`.
The selected promoted research architecture is `constrained_full_plus_feedback__buffer_capacity_g_m2_12p0`.

Stage 3 harvest-family context:
existing harvest-family docs and KNU harvest-family artifact were inspected.
Harvest-family behavior is treated as yield-semantics context, not as a replacement for one of A1-A4.

Stage 4 promotion gate:
A4 is not promotion-ready because it does not improve or match A3 on KNU direct measured-harvest fit.
Its lower collapse-day count does not compensate for worse KNU RMSE, negative R2, and fruit-anchor drift.

## Four-way architecture matrix

| Field | A1 `legacy_sink_baseline` | A2 `raw_thorp_direct_negative_control` | A3 `shipped_tomics_bounded_incumbent` | A4 `research_promoted_marginal_allocator` |
|---|---|---|---|---|
| Repo lane alias | `legacy_sink_baseline` | `raw_reference_thorp` | `incumbent_current` | `research_promoted` |
| Policy | `legacy` | `thorp_fruit_veg` | `tomics` | `tomics_promoted_research` |
| Fruit gate | Legacy tomato sink gate | Fruit weighted by sink fraction | Legacy fruit anchor | Legacy fruit anchor with optional feedback diagnostics |
| Vegetative split | Tomato-safe leaf/stem/root prior | THORP-derived vegetative split | Tomato-safe shoot split plus bounded root correction | Prior-weighted marginal leaf/stem/root optimizer |
| Leaf rule | Fixed tomato-safe shoot fraction | THORP leaf marginal proxy | LAI/leaf-share governor | Canopy marginal, optional sink penalty/turnover |
| Stem rule | Fixed tomato-safe shoot fraction | THORP stem/sapwood proxy | Residual shoot support | Support/transport/positioning marginal |
| Root rule | Small tomato empirical root fraction | Tree-style hydraulic/root dominance risk | Stress-gated bounded THORP root correction | Greenhouse multistress gate plus bounded THORP correction |
| THORP role | None | Direct negative-control allocator | Bounded hydraulic/root correction only | Bounded research cue only |
| Temporal memory | None | None | None beyond model state | Optional low-pass allocation/root target memory |
| Required states | Existing tomato legacy states | Existing tomato states plus THORP proxy inputs | Existing tomato states and water stress | Existing tomato states plus promoted diagnostics/reserve/buffer seams |
| Required parameters | Baseline split priors | THORP objective proxy constants | `wet_root_cap`, `dry_root_cap`, `lai_target_center`, leaf bounds | Optimizer, marginal modes, root gate, buffer/reserve, feedback modes |
| Hidden states | No extra allocator memory | No extra allocator memory | No extra allocator memory | `_promoted_*`, reserve/buffer/feedback diagnostics when enabled |
| Calibration budget | Baseline | Diagnostic only | Shared fair-validation budget | Must remain parity-bound; architecture knobs frozen |
| Known failure mode | Canopy collapse in current KNU window | Leaf fraction collapse and root over-allocation | Incumbent still shows collapse days in current artifact | Worse KNU measured-yield fit and fruit-anchor drift |
| Promotion eligibility | No; baseline only | No; negative control | Yes; incumbent | Research-only, not promotion-ready |
| Code location | `sink_based.py`, `policy.py` | `thorp_policies.py`, `thorp_opt.py` | `tomics_policy.py` | `promoted_policy.py`, `promoted_modes.py` |
| Config location | lane registry / factorial controls | lane registry / promoted P0 controls | `configs/exp/tomics_allocation_factorial.yaml` | current-vs-promoted promoted configs |
| Test/runner location | lane matrix tests/runners | lane matrix tests/runners | current-vs-promoted and lane matrix tests | promoted factorial and current-vs-promoted tests |

## A3 vs A4 focused comparison

KNU measured-yield artifacts favor A3 over A4.
A3 has `rmse_cumulative_offset = 15.8722` and `r2_cumulative_offset = 0.6939` in the representative observed-baseline comparison.
A4 has `rmse_cumulative_offset = 31.0563` and `r2_cumulative_offset = -0.1719` for the selected promoted architecture.
A4 reduces canopy-collapse days in the checked artifact from 31 to 6, but this does not clear the promotion gate because measured-yield fit and fruit-anchor preservation are worse.

A4 therefore remains useful as a research family for testing prior-weighted softmax, multistress root gating, temporal modes, reserve/buffer seams, and fruit feedback seams.
It must not replace the shipped A3 default until it matches or improves A3 on direct KNU measured harvest under calibration and hidden-state budget parity.

## Raw THORP failure diagnosis

A2 is diagnostic, not a candidate.
In the observed-baseline KNU artifact, the raw THORP-like control gives a superficially competitive offset RMSE, but the state behavior is biologically wrong for greenhouse tomato:

- mean leaf allocation fraction is `0.0449`
- mean root allocation fraction is `0.4614`
- canopy collapse days are `73`
- fruit allocation is sink-anchored, so the yield metric alone hides the vegetative failure

This confirms the value of A2 as a negative control and the need to keep THORP bounded inside TOMICS rather than making raw THORP the tomato master allocator.

## Harvest-family context audit

| Family | Validation-relevant semantics | Implementation status | Promotion implication |
|---|---|---|---|
| TOMSIM / Heuvelink | One common assimilate pool, source-sink partitioning, truss readiness, whole-truss harvest, linked leaf harvest | Native incumbent baseline | Keep as shipped comparator |
| TOMGRO / Jones | Age-structured leaves/stems/fruits, source-sink dynamics, dynamic picking/senescence, fruit-abortion research seam | Age-class scaffold exists; harvest outflow remains proxy-labelled | Comparator only |
| De Koning | Fruit developmental unit, vegetative-unit logic, FDS readiness, FDMC relation, first-fruit colour pruning | Current research harvest lead | Research context, not default replacement |
| Vanthoor | Explicit state-flow greenhouse yield model, carbohydrate buffer, fixed fruit boxcar, final-stage harvest flow, leaf pruning flow, floor-area basis | Strong medium-grained research family | Research context |
| Kuijpers | Common-structure scaffold for component comparison | Interface/scaffold, not a biology family | Useful for modular evaluation but not automatic identifiability |

The current KNU harvest-family selected artifact chooses `dekoning_fds|vegetative_unit_pruning|dekoning_fds` as the research lead, with native-state fraction 1.0 in that artifact.
That does not change the allocation recommendation: shipped TOMICS plus incumbent TOMSIM remains the production baseline until a harvest-aware promotion gate explicitly changes it.

## Metric summary

Representative direct KNU observed-baseline metrics:

| A | Architecture artifact row | RMSE offset | R2 offset | Final cumulative bias | Fruit anchor error | Collapse days | Mean fruit frac | Mean leaf frac | Mean root frac |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| A1 | `legacy_control` | 15.8724 | 0.6939 | 0.3677 | 0.0000 | 31 | 0.3406 | 0.4014 | 0.0860 |
| A2 | `raw_thorp_like_control` | 15.6956 | 0.7007 | -0.7096 | 0.0000 | 73 | 0.3406 | 0.0449 | 0.4614 |
| A3 | `shipped_tomics_control` | 15.8722 | 0.6939 | 0.3585 | 0.0000 | 31 | 0.3406 | 0.3872 | 0.0773 |
| A4 | `constrained_full_plus_feedback__buffer_capacity_g_m2_12p0` | 31.0563 | -0.1719 | 52.5236 | 0.1159 | 6 | 0.2247 | 0.4789 | 0.0728 |

The full default lane matrix was not regenerated because the longrun KNU yield xlsx path is absent locally.
This is a run-command blocker, not an architecture isolation blocker.

## State plausibility summary

A1 remains a useful biological baseline but does not solve collapse in the current KNU window.
A2 fails the tomato plausibility gate because root dominance and leaf collapse overwhelm any apparent RMSE advantage.
A3 preserves the legacy fruit anchor, keeps root bounded, and avoids raw THORP dominance.
A4 improves canopy-collapse days but shifts fruit allocation and measured-yield fit too far away from the incumbent.

## Identifiability and fairness assessment

The fair-validation surface freezes architecture-specific knobs and keeps shared calibration freedom explicit.
The existing budget manifest uses shared `fruit_load_multiplier` and `lai_target_center` tuning while keeping architecture-specific promoted knobs fixed.
That is the correct direction for parity, but A4 still carries more diagnostic and hidden runtime state than A3.
Promotion therefore requires proof that A4 wins without hidden-state or calibration-budget inflation.

Current evidence does not meet that bar.

## Promotion recommendation

- Keep A3 `shipped_tomics_bounded_incumbent` as the shipped production default.
- Keep A4 `research_promoted_marginal_allocator` as research-only.
- Keep A1 `legacy_sink_baseline` as the biological baseline.
- Keep A2 `raw_thorp_direct_negative_control` as a diagnostic negative control only.
- Do not promote on public RDA or public AI alone because both are review-only derived-DW lanes.
- Do not include `school_trait_bundle__yield` until its raw/sanitized observed-harvest blockers are resolved.

## Multi-dataset reproducibility follow-up

Issue #304 adds a reproducible A1-A4 lane-matrix config for `knu_actual`, `public_rda__yield`, and
`public_ai_competition__yield` under `configs/exp/tomics_a1_a4_multidataset_lane_matrix.yaml`.
This follow-up does not reopen the architecture decision from Issue #302 / PR #303.
The original decision remains unchanged unless a future measured-harvest promotion gate is explicitly reopened:
A3 remains the shipped incumbent and A4 remains research-only.

The config uses repo-relative sanitized fixtures and writes the review bundle to
`out/tomics_a1_a4_multidataset_lane_matrix/`.
It separates direct measured evidence from review-only public evidence:

| Dataset | Evidence grade | Decision weight | Promotion use |
|---|---|---|---|
| `knu_actual` | `direct_measured_harvest` | `promotion_gate` | Primary measured-harvest score only |
| `public_rda__yield` | `review_only_derived_dw` | `review_only_robustness` | Robustness / contradiction check only |
| `public_ai_competition__yield` | `review_only_derived_dw` | `review_only_robustness` | Public smoke / contradiction check only |

The public RDA and public AI competition lanes are useful for robustness, overfitting detection, and
directionality checks, but they are not promotion evidence because their observed harvest targets are
derived dry-weight estimates from public fresh-harvest or shipment measurements.
The lane gate therefore keeps `primary_measured_score.json` separate from
`review_only_public_score.json` and does not pool those values into one promotion score.
No raw/private KNU data are committed by this follow-up.

## Next minimal issue

After #304 lands, use the generated multi-dataset bundle to choose the next narrow validation dependency rather
than treating a KNU-only run as the final reproducibility claim.
