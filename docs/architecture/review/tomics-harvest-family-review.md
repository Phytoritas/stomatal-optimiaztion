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
| TOMGRO age-class harvest | research comparator | mixed; exact age-class scaffold plus proxy harvest outflow | `alloc/components/harvest/fruit_harvest_tomgro.py` | Mature-class harvest exists, but article-local harvest outflow detail is still treated as research proxy |
| De Koning FDS harvest | research high priority | exact-source for FDS readiness, leaf-colour rule, FDMC relations | `alloc/components/harvest/fruit_harvest_dekoning.py`, `alloc/components/harvest/fdmc.py`, `alloc/components/harvest/leaf_harvest.py` | Best fruit-level tomato harvest family in the current local corpus |
| Vanthoor boxcar harvest | research high priority | exact-source research family for fixed boxcar and explicit harvest outflow | `alloc/components/harvest/fruit_harvest_vanthoor.py`, `alloc/components/harvest/leaf_harvest.py` | Explicit `MCFruitHar` / `MCLeafHar` semantics make this the strongest medium-grained greenhouse family |
| Kuijpers scaffold | common interface only | exact-source scaffold | `alloc/components/partitioning/common_structure.py` plus harvest contracts | Not a standalone harvest biology family |

## Key conclusions

1. The incumbent baseline remains TOMSIM-like because the shipped tomato path already uses truss-level development semantics and that path is greenhouse-safe.
2. De Koning is the strongest fruit-level literature family for tomato-specific harvest and defoliation logic.
3. Vanthoor is the strongest medium-grained greenhouse harvest family because the appendix exposes explicit fruit and leaf harvest outflows.
4. TOMGRO remains useful as a comparator, but the available local harvest detail is still less exact than De Koning and Vanthoor.
5. Kuijpers is used only as the scaffold that separates allocator, harvest, and observation blocks.

## Current KNU research-family result

Under the runtime-complete harvest-family factorial on KNU actual data, the selected research harvest family resolves to:

- `dekoning_fds + vegetative_unit_pruning + dekoning_fds`

However, the current KNU window still shows weak research-family discrimination:

- `dekoning_fds`, `tomgro_ageclass`, and `vanthoor_boxcar` are effectively tied on cumulative and daily holdout error
- `dekoning_fds` is selected because the ranking still breaks that tie in its favor
- the runtime-complete probe still records proxy-heavy state reconstruction for the research families in this window

That makes `dekoning_fds` the current research lead, but not a promotion-grade replacement for shipped TOMICS plus incumbent TOMSIM harvest.
