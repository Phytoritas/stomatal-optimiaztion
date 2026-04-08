# TOMICS Lane Matrix Architecture

## Scope

This architecture adds one shared TOMICS-native comparison surface for:

- allocation lanes
- harvest profiles
- dataset roles

The lane matrix does **not** add a new tomato model type.
It continues to run the tomato pipeline through `pipeline.model = tomato_legacy` and changes comparison behavior only through:

- `partition_policy`
- harvest-profile selection
- dataset-role selection

## Comparison axes

### Allocation lanes

The public lane registry keeps five explicit allocation lanes:

- `legacy_sink_baseline` -> `partition_policy: legacy`
- `incumbent_current` -> `partition_policy: tomics`
- `research_current` -> `partition_policy: tomics_alloc_research`
- `research_promoted` -> `partition_policy: tomics_promoted_research`
- `raw_reference_thorp` -> `partition_policy: thorp_fruit_veg`

`raw_reference_thorp` and `legacy_sink_baseline` remain reference-only and diagnostic-only.

### Harvest profiles

Harvest semantics stay separate from allocation lanes.
The current registry keeps:

- `incumbent_harvest_profile`
- `locked_research_selected_harvest_profile`
- `diagnostic_factorial_harvest_profile`

The locked research profile resolves from the runtime-complete KNU harvest factorial winner.
If that artifact is missing, the matrix fails loudly instead of silently falling back.

### Dataset roles

Dataset role is resolved from contract plus metadata plus observation-family hints, not from family-name heuristics alone.
The public role surface is:

- `measured_harvest`
- `trait_plus_env_no_harvest`
- `env_only`
- `metadata_only`
- `yield_environment_only`

`yield_environment_only` is never auto-promoted to `measured_harvest`.
Promotion denominator math counts only `measured_harvest` datasets with an explicit harvested-cumulative contract.
That contract now requires sanitized fixture metadata for repo-side validation before a dataset can enter the promotion denominator.

## Scenario composition

Each `ComparisonScenario` is the product of:

- one allocation lane
- one harvest profile
- one dataset role assignment

This keeps comparison logic explicit and avoids hard-coding lane semantics into scorecards or gates.

## Canonical target and basis

The canonical public target remains:

- cumulative harvested fruit dry weight

The lane matrix never compares observed harvested cumulative mass against:

- latent on-plant fruit mass
- mature but unharvested on-plant mass
- internal fruit-buffer proxies

Input basis provenance is preserved through `reporting_basis_in`.
The public comparison basis remains `floor_area_g_m2` through `reporting_basis_canonical`.
Per-plant and floor-area series must not be mixed silently.
Per-plant measured-harvest sources are normalized to floor-area explicitly with `plants_per_m2` before scoring.

## Promotion surface vs diagnostic surface

The matrix writes two separate surfaces under `out/tomics/validation/lane-matrix/`.

### Promotion surface

Promotion aggregation only considers scenarios that are:

- promotion-eligible lanes
- non-reference lanes
- promotion-eligible harvest profiles
- `measured_harvest` datasets
- runtime-complete harvested-cumulative semantics
- post-writeback audit clean

### Diagnostic surface

The diagnostic surface may include:

- `legacy_sink_baseline`
- `raw_reference_thorp`
- non-promotable harvest profiles
- context-only datasets

In the current staged implementation, context-only dataset roles stay visible on the shared scorecard and diagnostic surface as explicit placeholder diagnostic rows.
They do not yet run observer/regime diagnostic metrics through the measured-harvest runtime.

Diagnostic winners must not be treated as promotion winners.

## Audit-first gating

Promotion stays blocked when any audit seam fails:

- all-zero harvest series
- dropped non-harvested mass after writeback
- off-plant positive mass
- unresolved harvested-cumulative semantics
- unresolved basis normalization

This audit-first rule is lane-level for promotion.
If any measured dataset row fails a writeback or basis audit, that lane/profile remains visible diagnostically but cannot pass promotion.

When multi-dataset support is present, promotion also stays blocked if:

- fewer than two measured datasets support the candidate
- `native_state_coverage < 0.5`
- `shared_tdvs_proxy_fraction > 0.5`
- `cross_dataset_stability_score < 0.5`

## Artifact tree

The shared lane-matrix root is:

- `out/tomics/validation/lane-matrix/`

Key artifacts are:

- `matrix_spec.json`
- `resolved_matrix_spec.json`
- `scenario_index.csv`
- `dataset_role_summary.csv`
- `lane_scorecard.csv`
- `promotion_surface.csv`
- `diagnostic_surface.csv`
- `lane_gate_decision.json`
- `scenarios/<scenario_id>/...`

The existing `out/tomics/validation/knu/` tree remains unchanged.
