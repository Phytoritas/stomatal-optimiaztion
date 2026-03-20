# TOMICS Tomato Partitioning

## Overview

This repository now treats `TOMICS` as the canonical tomato-facing umbrella framework:

- `TOMICS-Alloc`
- `TOMICS-Flux`
- `TOMICS-Grow`

The current tomato legacy pipeline still runs through `pipeline.model = tomato_legacy`. The new `tomics` partition policy plugs into the existing `pipeline.partition_policy` path and does not introduce a new tomato model type.

## Policy comparison

| Policy | Fruit allocation | Vegetative split | Greenhouse awareness | Main risk |
|---|---|---|---|---|
| `legacy` | legacy sink law only | fixed 70/30 shoot split plus legacy root fraction | low | root response can be too static |
| `thorp_fruit_veg` | sink-weighted fruit fraction | direct THORP-derived leaf/stem/root split | weak | raw THORP root dominance can over-allocate belowground biomass for greenhouse tomato |
| `tomics` | legacy sink law anchored exactly | bounded THORP-informed root correction plus LAI-governed shoot split | high | depends on bounded stress proxies; falls back to legacy-like behavior when missing |

## Why the fruit-vs-vegetative split stays on the legacy sink law

Tomato fruit versus vegetative demand still shares one common assimilate pool in the staged legacy pipeline. `TOMICS-Alloc` therefore keeps fruit allocation anchored to the same sink proxy that the legacy tomato path already uses. THORP-derived information is not allowed to overwrite fruit demand directly; it only informs a bounded correction inside the vegetative partition.

## Why canopy collapse must be prevented

Greenhouse tomato performance remains sensitive to maintaining enough leaf area to support canopy function, intercepted radiation, and continued fruit filling. A raw THORP vegetative split can push too much allocation into roots under stress proxies that matter more for field trees than greenhouse tomato. `tomics` therefore keeps the base shoot prior at leaf/stem = `0.70/0.30` and adds an LAI governor around a default target band centered near `2.75`.

## Why greenhouse tomato needs bounded root correction

The migrated tomato legacy path exposes `theta_substrate` and a bounded `water_supply_stress` proxy. Those greenhouse/rootzone signals are useful, but they do not justify letting raw THORP dominate the full plant allocation outcome. `tomics` therefore:

- preserves the legacy fruit fraction
- uses THORP only to inform the root correction direction
- caps root allocation near `0.10` under wet conditions and near `0.18` under dry conditions
- falls back toward legacy-like behavior when stress inputs are missing

## Current integration points

- policy registry: `src/stomatal_optimiaztion/domains/tomato/tomics/alloc/components/partitioning/policy.py`
- TOMICS hybrid policy: `src/stomatal_optimiaztion/domains/tomato/tomics/alloc/components/partitioning/tomics_policy.py`
- tomato legacy model policy hook: `src/stomatal_optimiaztion/domains/tomato/tomics/alloc/models/tomato_legacy/tomato_model.py`
- config-driven pipeline entry: `src/stomatal_optimiaztion/domains/tomato/tomics/alloc/pipelines/tomato_legacy.py`
- canonical tomato-facing namespace: `src/stomatal_optimiaztion/domains/tomato/tomics/`

## Example configs

### Legacy

```yaml
pipeline:
  model: tomato_legacy
  partition_policy: legacy
  allocation_scheme: 4pool
  theta_substrate: 0.33
```

### Raw THORP

```yaml
pipeline:
  model: tomato_legacy
  partition_policy: thorp_fruit_veg
  allocation_scheme: 4pool
  theta_substrate: 0.33
```

### TOMICS

```yaml
pipeline:
  model: tomato_legacy
  partition_policy: tomics
  allocation_scheme: 4pool
  theta_substrate: 0.33
  tomics:
    wet_root_cap: 0.10
    dry_root_cap: 0.18
    lai_target_center: 2.75
```
