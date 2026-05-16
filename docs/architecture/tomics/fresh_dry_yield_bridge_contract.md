# Fresh/Dry Yield Bridge Contract

Goal 3A.5 may bridge fresh/dry yield values from legacy v1.3 derived outputs with explicit provenance. These outputs are not raw observations.

Fresh yield fields such as `loadcell_daily_yield_g`, `loadcell_cumulative_yield_g`, and `final_fresh_yield_g` are treated as measured-or-legacy fresh-yield bridge values when their source passes schema checks.

Dry yield fields with DMC labels are estimated dry-yield bases:

- `default_5p6pct`
- `lower_5p2pct`
- `upper_6p0pct`
- `broad_low_4pct`
- `broad_high_8pct`

DMC-derived dry yield is an estimated dry-yield basis, not direct destructive dry-mass measurement unless separately verified. The legacy default DMC is `0.056`; the configured TOMICS default remains `0.065`. Harvest-family validation must run DMC sensitivity later.
