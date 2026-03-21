# TOMICS Harvest Equation Manifest

This document narrows the harvest-specific subset of the broader TOMICS source/equation manifests.

Evidence note:

- Repo-local paper copies under `docs/references/source_papers/` were used where present.
- Zotero was used as a second evidence surface for metadata sanity checks on all five harvest-family papers.
- For Vanthoor `2011`, exact appendix equations were cross-checked against Zotero appendix item `SIZ3ZU3W` and attachment `CKLNUS4Q`; the repo-local `...yiel 1.pdf` article attachment corresponds to appendix text in Zotero and should not be treated as independent article evidence.
- Current public harvest families do not all run on literature-native state representations. Where the runtime only reinterprets legacy TOMSIM state through a normalized adapter, the row is marked `source-grounded proxy adapter` rather than `exact-source`.

| Source | Harvest equation or rule | Current code path | Status |
|---|---|---|---|
| Heuvelink `1996` / TOMSIM | Eq. `[2]` truss appearance rate and Eq. `[1]` Richards-derivative potential growth anchor the legacy truss state used by harvest readiness | `alloc/models/tomato_legacy/tomato_model.py`, `alloc/components/harvest/state_normalizer.py` | exact-source baseline input |
| Heuvelink `1996` / TOMSIM | `TDVS = 1` harvest readiness for the reference fruit / harvestable truss | `alloc/components/harvest/readiness.py`, `alloc/components/harvest/fruit_harvest_tomsim.py` | exact-source baseline |
| Heuvelink `1996` / TOMSIM | whole-truss dry-matter removal at harvest | `alloc/components/harvest/fruit_harvest_tomsim.py` | exact-source baseline |
| Heuvelink `1996` / TOMSIM | linked-truss stage leaf removal threshold | `alloc/components/harvest/leaf_harvest.py` | source-grounded management proxy |
| Jones et al. `1991` / TOMGRO | age-class state transport / mature class harvest | `alloc/components/harvest/fruit_harvest_tomgro.py` | mixed exact-source structure + proxy harvest outflow |
| De Koning `1994` | Eq. `3.2.3` / `FDS >= threshold` fruit harvest readiness | `alloc/components/harvest/readiness.py`, `alloc/components/harvest/fruit_harvest_dekoning.py` | exact-source research subrule |
| De Koning `1994` | first-fruit colour linked leaf harvest trigger | `alloc/components/harvest/leaf_harvest.py` | source-grounded management proxy |
| De Koning `1994` | Eq. `4.2.2` and `4.2.3` FDMC relations | `alloc/components/harvest/fdmc.py` | exact-source research subrule |
| De Koning `1994` | Eq. `4.4.1` and `4.4.2` diameter-to-fresh-weight relations | not yet coded in the current harvest runtime | traced but deferred |
| Vanthoor `2011` appendix | Eq. `(2)`, `(24)`, `(26)`, `(31)`-`(34)`, `(47)` define the native boxcar train and harvest/pruning flows | `alloc/components/harvest/fruit_harvest_vanthoor.py`, `alloc/components/harvest/leaf_harvest.py` | traced source; current runtime is a source-grounded proxy adapter |
| Vanthoor `2011` appendix | explicit `MCFruitHar` / `DMHar` outflow semantics | `alloc/components/harvest/readiness.py`, `alloc/components/harvest/fruit_harvest_vanthoor.py` | source-grounded proxy adapter |
| Vanthoor `2011` appendix | `MCLeafHar` / `MaxLAI` pruning flow | `alloc/components/harvest/leaf_harvest.py` | source-grounded proxy adapter |
| Kuijpers `2019` | Eq. `(5)` `h1` fruit harvest, `h2` leaf harvest scaffold mapping | `alloc/components/harvest/contracts.py`, `alloc/components/partitioning/common_structure.py` | exact-source scaffold |
| Kuijpers `2019` | repo residual mass backfill into leaf vs stem/root | `alloc/components/partitioning/common_structure.py` | reporting fallback, not a Kuijpers equation |
