# TOMICS Harvest Family Review

## Scope

This review re-opened the local full texts for:

- Heuvelink `1996` / TOMSIM
- Jones et al. `1991` / TOMGRO
- De Koning `1994`
- Vanthoor `2011` article
- Vanthoor `2011` electronic appendix
- Kuijpers `2019`

The implementation rule is strict:

- exact-source equations are marked as exact-source only when the local source text was traced in the manifest
- otherwise the path is marked as research proxy

## Family summary

| Family | Role | Exact-source status | Current code path | Notes |
|---|---|---|---|---|
| TOMSIM truss harvest | incumbent baseline | exact-source baseline | `alloc/components/harvest/fruit_harvest_tomsim.py` | Truss readiness from `TDVS`, whole-truss harvest mass, linked-truss leaf removal baseline |
| TOMGRO age-class harvest | research comparator | source-grounded proxy adapter | `alloc/components/harvest/fruit_harvest_tomgro.py` | Mature-class harvest exists, but the public runtime still uses a proxy adapter rather than a native TOMGRO mature-pool implementation |
| De Koning FDS harvest | research high priority | mixed; exact-source readiness and FDMC subrules plus proxy adapter runtime | `alloc/components/harvest/fruit_harvest_dekoning.py`, `alloc/components/harvest/fdmc.py`, `alloc/components/harvest/leaf_harvest.py` | Strongest fruit-level tomato literature family in the current local corpus, but not yet a native end-to-end runtime |
| Vanthoor boxcar harvest | research high priority | source-grounded proxy adapter with appendix-traced outflow semantics | `alloc/components/harvest/fruit_harvest_vanthoor.py`, `alloc/components/harvest/leaf_harvest.py` | Explicit `MCFruitHar` / `MCLeafHar` semantics make this the strongest medium-grained greenhouse family, but native fixed-boxcar runtime remains deferred |
| Kuijpers scaffold | common interface only | exact-source scaffold | `alloc/components/partitioning/common_structure.py` plus harvest contracts | Not a standalone harvest biology family |

## Key conclusions

1. The incumbent baseline remains TOMSIM-like because the shipped tomato path already uses truss-level development semantics and that path remains the only promotion-grade public baseline.
2. De Koning remains the strongest fruit-level literature family for tomato-specific harvest and defoliation logic.
3. Vanthoor remains the strongest medium-grained greenhouse research family, and the current KNU shortlist still selects `vanthoor_boxcar + max_lai_pruning_flow + constant_observed_mean`.
4. TOMGRO remains useful as a comparator, but the public runtime still exposes it as a source-grounded proxy adapter rather than a native tomato harvest runtime.
5. Kuijpers is used only as the scaffold that separates allocator, harvest, and observation blocks.

## Current KNU research-family result

Under the current harvest-family factorial on KNU actual data, the best research harvest family is:

- `vanthoor_boxcar + max_lai_pruning_flow + constant_observed_mean`

That result survives the repaired zero-yield replay and post-writeback audit, but it still does not improve holdout promotion-gate performance enough to replace shipped TOMICS plus incumbent TOMSIM harvest.
