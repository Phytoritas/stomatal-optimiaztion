# public_rda measured-harvest preprocessing spec

## Scope

This note records the `public_rda__yield` preprocessing and registry contract now landed on
`main` through issue `#284` / PR `#285`.

This document covers only `public_rda__yield`. It does not cover
`school_trait_bundle__yield`, `public_ai_competition__yield`, lane-matrix changes,
KNU private data, or public promotion-policy changes.

## Decision

`public_rda__yield` is accepted as a `RUNNABLE` measured-harvest-compatible dataset
for public cross-dataset plumbing only with an explicit proxy-derived caveat.

This dataset is not a direct measured fruit dry-weight series.

Accepted semantics:

- source observed quantity: measured fresh shipment mass from the public RDA sale workbook
- validation target quantity: cumulative total fruit dry mass on floor-area basis
- derivation label: `derived_dw_from_measured_fresh_shipment`
- `is_direct_dry_weight = false`
- `uses_literature_dry_matter_fraction = true`
- `review_flag = review_only_dry_matter_conversion`

`review_only_dry_matter_conversion` is preserved as a review flag and caveat, not as
a hard blocker, for this accepted derived-DW runtime path.

## Representative runnable slice

The repo-local sanitized fixture package uses one representative public RDA slice:

- `2018_farm10_season1_ripe_tomato`

Repo-relative fixture package:

- `data/fixtures/public_rda_sanitized/2018_farm10_season1_ripe_tomato/forcing_fixture.csv`
- `data/fixtures/public_rda_sanitized/2018_farm10_season1_ripe_tomato/observed_harvest_fixture.csv`
- `data/fixtures/public_rda_sanitized/2018_farm10_season1_ripe_tomato/provenance.md`

External complete-slice catalog used during intake:

- `outputs/traitenv/fixtures/public_rda_yield/usable_complete_slices.csv`

Complete-slice intake summary:

- complete unique slices: `246`
- `2018 = 61`
- `2019 = 63`
- `2020 = 61`
- `2021 = 61`

## Source workbooks

Representative source workbooks:

- `2018_sale.xlsx`
- `2018_env.xlsx`
- `2018_cultInfo.xlsx`

Representative provenance records:

- cultivar: `deirose`
- greenhouse kind: `vinyl`
- plant density: `4.0`
- canonical floor-area source: cultivation total floor area
- floor-area denominator: `1000.0 m^2`

## Runtime fixture contract

Forcing fixture required columns:

- `datetime`
- `T_air_C`
- `PAR_umol`
- `CO2_ppm`
- `RH_percent`
- `wind_speed_ms`

Representative forcing range:

- `2018-10-26 00:00:00 -> 2019-06-30 23:00:00`

Observed harvest fixture required columns:

- `Date`
- `Measured_Cumulative_Total_Fruit_DW (g/m^2)`

Representative observed sale range:

- `2019-01-17 -> 2019-06-30`

Accepted validation overlap:

- `2019-01-17 -> 2019-06-30`

## Basis and derivation contract

Accepted reporting basis:

- `floor_area_g_m2`

Supporting provenance:

- `plants_per_m2 = 4.0`
- plant density is supporting metadata because the runtime target is already floor-area normalized

Accepted derivation:

- raw observed quantity: total shipment mass
- assumption: the sale workbook shipment column is treated as fresh shipment mass in kg
- daily rule: aggregate fresh shipment mass by date, then cumulative sum
- dry-matter baseline: `0.065`
- dry-matter sensitivity range: `0.05 -> 0.09`
- baseline formula: `cumulative_DW_g_per_m2 = cumsum(sum(raw_total_shipment_kg_by_day) * 1000 * 0.065) / floor_area_g_m2`

Required caveat:

- this is a proxy conversion from fresh shipment mass
- it is not a direct measured fruit dry-weight time series

## Registry contract

The canonical `public_rda__yield` registry row keeps these fields explicit:

- `ingestion_status = runnable`
- `reporting_basis = floor_area_g_m2`
- `date_column = Date`
- `measured_cumulative_column = Measured_Cumulative_Total_Fruit_DW (g/m^2)`
- `observed_harvest_derivation = derived_dw_from_measured_fresh_shipment`
- `is_direct_dry_weight = false`
- `uses_literature_dry_matter_fraction = true`
- `review_flags = ["review_only_dry_matter_conversion"]`
- repo-relative forcing and observed harvest fixture paths under `data/fixtures/public_rda_sanitized`
- provenance tags including `derived_dw_proxy`

The registry may count `public_rda__yield` as a runnable harvest-validation dataset
for scorecard breadth and cross-dataset diagnostics. Promotion-grade conclusions must
still expose and guard the review-only derived-DW caveat.

## Non-claims

This decision does not claim that `public_rda__yield` is a direct measured fruit dry-weight
dataset. It does not weaken public promotion semantics. It does not register KNU private
raw data, and it does not register `school_trait_bundle__yield` or change
`public_ai_competition__yield` semantics.
