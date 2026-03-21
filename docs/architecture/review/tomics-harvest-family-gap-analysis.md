# TOMICS Harvest Family Gap Analysis

## Exact-source subrules completed

- TOMSIM truss readiness and whole-truss harvest
- De Koning `FDS >= threshold` harvest readiness
- De Koning FDMC functions in `fds` and harvest-time modes
- Kuijpers `h1` / `h2` scaffold mapping

## Research-proxy seams still explicit

- TOMGRO harvest outflow remains a mature-class / mature-pool proxy because the current local paper pass does not expose a cleaner committed harvest flux law than the age-class maturity structure itself
- TOMGRO leaf harvest remains management-linked rather than a fully exact-source pruning rule
- TOMSIM linked-truss leaf harvest thresholding is source-grounded but still parameterized as a management proxy
- De Koning leaf removal thresholding is source-grounded but still implemented as a management proxy
- De Koning fresh-weight reporting does not yet use Eq. `4.4.1` / `4.4.2` diameter-to-fresh-weight relations
- De Koning fruit-position weighting remains a documented research seam rather than an exact-source committed production law
- Vanthoor current runtime remains a source-grounded proxy adapter on legacy-normalized state rather than a full native fixed-boxcar implementation
- Vanthoor stem-root back-mapping is a reporting map, not a claimed literature stem/root split
- Kuijpers 70/30 residual mass backfill is a repo reporting fallback, not a source equation

## What still remains deferred

- family-specific calibration beyond the current reduced KNU harvest screening
- richer fruit-position weighting inside De Koning harvest events
- exact measured EC / root-zone temperature override data for the De Koning harvest-time FDMC path
- measured greenhouse pruning-management logs to replace current harvest-delay / leaf-removal management assumptions

## Decision

The current repository now has a literature-aware harvest family layer, but the promotion gate still does not justify changing the public incumbent baseline.
