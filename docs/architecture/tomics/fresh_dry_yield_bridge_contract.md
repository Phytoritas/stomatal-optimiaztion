# Fresh/Dry Yield Bridge Contract

Goal 3A.5 may bridge fresh/dry yield values from legacy v1.3 derived outputs with explicit provenance. These outputs are not raw observations.

Fresh yield fields such as `loadcell_daily_yield_g`, `loadcell_cumulative_yield_g`, and `final_fresh_yield_g` are treated as measured-or-legacy fresh-yield bridge values when their source passes schema checks.

For the 2025-2C TOMICS-HAF analysis, fruit DMC is fixed at `0.056`.

Dry yield fields with 5.6% DMC labels are mapped to the canonical 2025-2C dry-yield basis:

- `default_5p6pct`
- `final_dry_yield_g_est_5p6pct`
- `dry_yield_5p6pct`

Other legacy DMC-labeled columns may be audited as provenance-only sensitivity columns, not current 2025-2C primary metrics:

- `lower_5p2pct`
- `upper_6p0pct`
- `broad_low_4pct`
- `broad_high_8pct`
- historical or deprecated previous-default `0.065` / 6.5% columns

Dry yield derived from fresh yield using DMC `0.056` is an estimated dry-yield basis, not direct destructive dry-mass measurement unless separately verified.

DMC sensitivity is disabled for the current 2025-2C run unless explicitly re-enabled in a later goal. Any prior `0.065` DMC references are deprecated previous-default notes and must not drive 2025-2C metrics.

Harvest-family ranking, observation operators, and promotion gate must use DMC `0.056` for 2025-2C.
