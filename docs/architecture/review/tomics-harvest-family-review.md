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

## Evidence handles

The harvest review was cross-checked against both the repo-local paper folder and Zotero metadata/attachments:

- Heuvelink `1996`
  - repo-local PDF: `docs/references/source_papers/Heuvelink - 1996 - Tomato growth and yield  quantitative analysis and synthesis.pdf`
  - Zotero item key: `HHD63E6H`
- Jones et al. `1991` / TOMGRO
  - repo-local PDF: `docs/references/source_papers/J. W. Jones et al. - 1991 - A DYNAMIC TOMATO GROWTH AND YIELD MODEL (TOMGRO).pdf`
  - Zotero item key: `JZMAF7MV`
- De Koning `1994`
  - repo-local PDF: `docs/references/source_papers/De Koning - 1994 - Development and dry matter distribution in glasshouse tomato  a quantitative approach.pdf`
  - Zotero item key: `RT8W6KUD`
- Vanthoor `2011` article
  - repo-local PDFs: `docs/references/source_papers/Vanthoor et al. - 2011 - A methodology for model-based greenhouse design Part 2, description and validation of a tomato yiel.pdf` and `...yiel 1.pdf`
  - Zotero article item key: `VYCHQ7HV`
- Vanthoor `2011` electronic appendix
  - Zotero parent item key: `SIZ3ZU3W`
  - Zotero PDF attachment key: `CKLNUS4Q`
  - note: the repo-local `...yiel 1.pdf` attachment resolves to appendix text in Zotero (`GRN6KBKD`), so exact appendix equations were cross-checked from Zotero rather than assumed from filename alone
- Kuijpers `2019`
  - repo-local PDF: `docs/references/source_papers/Kuijpers et al. - 2019 - Model selection with a common structure Tomato crop growth models.pdf`
  - Zotero item key: `5F5FUHIM`

## Family summary

| Family | Role | Exact-source status | Current code path | Notes |
|---|---|---|---|---|
| TOMSIM truss harvest | incumbent baseline | exact-source baseline for `TDVS` readiness and whole-truss removal; linked leaf-stage parameterization remains a management proxy | `alloc/components/harvest/fruit_harvest_tomsim.py`, `alloc/components/harvest/leaf_harvest.py` | Legacy TOMSIM truss state is the public baseline and the only harvest family currently running on literature-native state semantics rather than a normalized adapter |
| TOMGRO age-class harvest | research comparator | mixed; exact age-class scaffold plus proxy harvest outflow | `alloc/components/harvest/fruit_harvest_tomgro.py` | Mature-class harvest exists, but current runtime still consumes legacy-normalized state plus `mature_pool_delta_g_m2` proxy inputs |
| De Koning FDS harvest | research high priority | mixed; `FDS` readiness and FDMC helpers are exact-source, but leaf-pruning thresholding and fresh-weight reporting are proxy adapters | `alloc/components/harvest/fruit_harvest_dekoning.py`, `alloc/components/harvest/fdmc.py`, `alloc/components/harvest/leaf_harvest.py` | Best fruit-level tomato harvest family in the current local corpus, but not yet a full literature-native fruit/vegetative-unit runtime |
| Vanthoor boxcar harvest | research high priority | source-grounded proxy adapter; appendix equations are traced, but the public runtime is not yet a full native Vanthoor fixed-boxcar implementation | `alloc/components/harvest/fruit_harvest_vanthoor.py`, `alloc/components/harvest/leaf_harvest.py` | Current code uses legacy-normalized stage state, `n_dev=5` defaults, and proxy outflow fallbacks rather than the appendix-native `nDev=50` stage train and full `MCFruitHar` / `MCLeafHar` state flow |
| Kuijpers scaffold | common interface only | exact-source scaffold for `h1` / `h2`; repo mass backfilling remains a reporting fallback | `alloc/components/partitioning/common_structure.py` plus harvest contracts | Not a standalone harvest biology family, and the repo-local residual mass split should not be read as a Kuijpers source claim |

## Key conclusions

1. The incumbent baseline remains TOMSIM-like because the shipped tomato path already uses truss-level development semantics and that path is greenhouse-safe.
2. De Koning is the strongest fruit-level literature family for tomato-specific harvest and defoliation logic, but the current public runtime only implements the `FDS` / FDMC subrules exactly.
3. Vanthoor is the strongest medium-grained greenhouse harvest family in the literature corpus because the appendix exposes explicit fruit and leaf harvest outflows, but the current public runtime is still a source-grounded proxy adapter rather than a full native Vanthoor stage train.
4. TOMGRO remains useful as a comparator, but the available local harvest detail is still less exact than De Koning and Vanthoor and the current runtime keeps harvest outflow proxy-labelled.
5. Kuijpers is used only as the scaffold that separates allocator, harvest, and observation blocks; repo reporting fallbacks are not treated as Kuijpers equations.

## Current KNU research-family result

Under the current harvest-family factorial on KNU actual data, the best research harvest family is:

- `vanthoor_boxcar + max_lai_pruning_flow + constant_observed_mean`

That result improves canopy-management behaviour relative to the incumbent harvest baseline, but it does not improve holdout promotion-gate performance enough to replace shipped TOMICS plus incumbent TOMSIM harvest.
