# TOMICS Naming Migration

## Mapping

| Old tomato-facing name | New canonical name | Status |
|---|---|---|
| `tGOSM` | `TOMICS-Flux` | canonical tomato-facing runtime name; legacy label retained only in provenance documents |
| `tTHORP` | `TOMICS-Alloc` | canonical tomato-facing runtime name; legacy label retained only in provenance documents |
| `tTDGM` | `TOMICS-Grow` | canonical tomato-facing runtime name; legacy label retained only in provenance documents |

## What was renamed

- tomato-facing README, script help text, plot titles, and example config surfaces
- tomato-facing public namespace via `src/stomatal_optimiaztion/domains/tomato/tomics/`
- tomato-facing package display constants through `CANONICAL_MODEL_NAME`
- tomato-facing policy registry aliases via `tomics`, `tomics_alloc`, and `tomics_hybrid`

## What was intentionally not renamed

- root-domain `THORP`, `GOSM`, and `TDGM` package names
- archived `TOMATO/tTHORP`, `TOMATO/tGOSM`, and `TOMATO/tTDGM` provenance references inside migration-history documents
- raw policy aliases such as `thorp_veg`, `thorp_fruit_veg`, and `thorp_4pool`
- THORP equation helper modules such as `thorp_opt.py`

## Compatibility aliases and shims

- canonical implementation folders now live under `domains/tomato/tomics/alloc`, `domains/tomato/tomics/flux`, and `domains/tomato/tomics/grow`
- the old physical package folders `domains/tomato/tthorp`, `domains/tomato/tgosm`, and `domains/tomato/ttdgm` were removed
- legacy runtime import paths were retired; live code must import from `domains.tomato.tomics.*`
- canonical TOMICS names are added through the new `domains/tomato/tomics/` packages while the existing partition-policy family still resolves through the same tomato legacy pipeline

## Preserved provenance

- architecture inventory and module-spec history still mention `tTHORP`, `tGOSM`, and `tTDGM` where those names identify the original migration slices
- public/runtime tomato-facing surfaces use only `TOMICS-*` names
- `out/tomics_naming_audit/rename_manifest.csv` records which surfaces were renamed, retired from runtime, or preserved as provenance
