# TOMICS KNU Root-Zone Inversion

## Purpose

Issue `#239` / module `118` replaces the old single-pass substrate proxy with an irrigation-aware root-zone reconstruction bundle and explicit uncertainty reporting.

## Supported modes

Current actual-data mode:

- `theta_proxy_mode = bucket_irrigated`

Scenario labels:

- dry
- moderate
- wet

Hard bounds:

- `theta_min_hard = 0.40`
- `theta_max_hard = 0.85`

## Current actual-data summary

Output root:

- `out/tomics_knu_rootzone_reconstruction/`

Current scenario summaries:

- dry mean theta: `0.4573`
- moderate mean theta: `0.5989`
- wet mean theta: `0.7488`
- proxy uncertainty width: `0.2915`
- oversaturation days: `0`
- rootzone stress activation days: `9`

## Assumptions

- greenhouse-soilless bounds remain conservative and explicit
- irrigation timing is inferred when measured irrigation is absent
- measured root-zone variables may override the proxy later if supplied
