# TOMICS Harvest Family Gap Analysis

## Exact-source paths completed

- TOMSIM truss readiness and whole-truss harvest
- TOMSIM linked-truss leaf harvest threshold handling
- De Koning `FDS >= threshold` harvest readiness
- De Koning vegetative-unit / first-fruit-colour leaf harvest rule
- De Koning FDMC functions in `fds` and harvest-time modes
- Vanthoor fixed boxcar last-stage harvest semantics
- Vanthoor max-LAI pruning flow / explicit leaf-harvest seam
- Kuijpers `h1` / `h2` scaffold mapping

## Research-proxy seams still explicit

- TOMGRO harvest outflow remains a mature-class / mature-pool proxy because the current local paper pass does not expose a cleaner committed harvest flux law than the age-class maturity structure itself
- TOMGRO leaf harvest remains management-linked rather than a fully exact-source pruning rule
- De Koning fruit-position weighting remains a documented research seam rather than an exact-source committed production law
- Vanthoor stem-root back-mapping is a reporting map, not a claimed literature stem/root split

## What still remains deferred

- family-specific calibration beyond the current reduced KNU harvest screening
- richer fruit-position weighting inside De Koning harvest events
- exact measured EC / root-zone temperature override data for the De Koning harvest-time FDMC path
- measured greenhouse pruning-management logs to replace current harvest-delay / leaf-removal management assumptions

## Runtime-complete rerun reading

Issue `#255` removes the missing post-maturity runtime-state blocker as the main explanation for the current KNU rerun outcome.

- the sanity probe now sees populated `matured_at`, `days_since_maturity`, `sink_active_flag`, and step-flux harvest outputs on the actual-data lane
- the current KNU window still leaves `tomgro_ageclass`, `dekoning_fds`, and `vanthoor_boxcar` on a `shared_tdvs_proxy` surface with `proxy_mode_used = true`
- the rerun does not observe partial outflow in this window, so that path stays contract-complete but empirically unused here
- the selected research family is now `dekoning_fds`, but the research families remain effectively tied on validation metrics

## Decision

The current repository now has a literature-aware and runtime-complete harvest family layer, but the promotion gate still does not justify changing the public incumbent baseline.

The correct interpretation is no longer "the harvest runtime is missing." It is "runtime-complete harvest reruns still show weak family discrimination on the current KNU window."
