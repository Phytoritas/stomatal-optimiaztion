# Issue 243 Executor Record

## Title

[Harvest Architecture] Complete TOMICS literature-aware harvest family pipeline and harvest-aware promotion gate on KNU data

## Scope

- add a first-class harvest layer under `alloc/components/harvest/`
- separate allocator family, harvest family, observation operator, and calibration parity
- implement TOMSIM, TOMGRO, De Koning, and Vanthoor harvest-family paths
- connect harvest-family outputs back into KNU validation and promotion-gate workflows
- keep shipped `partition_policy: tomics` unchanged

## Output roots

- `out/tomics_knu_harvest_family_factorial/`
- `out/tomics_knu_harvest_promotion_gate/`

## Decision

Shipped TOMICS plus incumbent TOMSIM harvest remains the incumbent baseline.

The best research harvest family remains research-only.
