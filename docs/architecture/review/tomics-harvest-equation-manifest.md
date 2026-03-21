# TOMICS Harvest Equation Manifest

This document narrows the harvest-specific subset of the broader TOMICS source/equation manifests.

| Source | Harvest equation or rule | Current code path | Status |
|---|---|---|---|
| Heuvelink `1996` / TOMSIM | `TDVS >= 1` truss harvest readiness | `alloc/components/harvest/readiness.py`, `alloc/components/harvest/fruit_harvest_tomsim.py` | exact-source baseline |
| Heuvelink `1996` / TOMSIM | whole-truss dry-matter removal at harvest | `alloc/components/harvest/fruit_harvest_tomsim.py` | exact-source baseline |
| Heuvelink `1996` / TOMSIM | linked-truss stage leaf harvest | `alloc/components/harvest/leaf_harvest.py` | exact-source baseline |
| Jones et al. `1991` / TOMGRO | age-class state transport / mature class harvest | `alloc/components/harvest/fruit_harvest_tomgro.py` | mixed exact-source structure + proxy harvest outflow |
| De Koning `1994` | `FDS >= threshold` fruit harvest readiness | `alloc/components/harvest/readiness.py`, `alloc/components/harvest/fruit_harvest_dekoning.py` | exact-source research |
| De Koning `1994` | first-fruit colour linked leaf harvest | `alloc/components/harvest/leaf_harvest.py` | exact-source research |
| De Koning `1994` | `FDMC(FDS)` and harvest-time FDMC relation | `alloc/components/harvest/fdmc.py` | exact-source research |
| Vanthoor `2011` appendix | final-stage `MCFruitHar` boxcar outflow semantics | `alloc/components/harvest/readiness.py`, `alloc/components/harvest/fruit_harvest_vanthoor.py` | exact-source research |
| Vanthoor `2011` appendix | `MCLeafHar` / `MaxLAI` pruning flow | `alloc/components/harvest/leaf_harvest.py` | exact-source research |
| Kuijpers `2019` | `h1` fruit harvest, `h2` leaf harvest scaffold mapping | `alloc/components/harvest/contracts.py`, `alloc/components/partitioning/common_structure.py` | exact-source scaffold |
