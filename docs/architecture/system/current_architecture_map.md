# Current Architecture Map

## Entry Points
- `scripts/run_tomics_multidataset_harvest_factorial.py` runs the measured-harvest multidataset comparison lanes.
- `scripts/run_tomics_multidataset_harvest_promotion_gate.py` evaluates the mixed/public multidataset promotion gate.
- `scripts/run_tomics_lane_matrix.py` and `scripts/run_tomics_lane_matrix_gate.py` cover lane-matrix scorecard and gate surfaces.
- `scripts/run_tomics_knu_*` scripts exercise KNU calibration, observation evaluation, harvest family comparison, state reconstruction, and rootzone reconstruction.
- `scripts/build_knu_rootzone_sanitized.py` and `scripts/build_knu_rootzone_aligned_fixture.py` prepare local KNU rootzone/EC diagnostic fixtures.

## Core Modules
- `src/stomatal_optimiaztion/domains/tomato/tomics/alloc/validation/datasets/contracts.py` defines dataset ingestion status, capability, basis, observation, dry-matter conversion, fixture, and management contracts.
- `src/stomatal_optimiaztion/domains/tomato/tomics/alloc/validation/datasets/registry.py` builds the runnable/draft dataset registry from config overlays plus the KNU data contract.
- `src/stomatal_optimiaztion/domains/tomato/tomics/alloc/validation/datasets/metadata.py` exposes registry frames, blocker frames, review flags, and proxy-derived caveats.
- `src/stomatal_optimiaztion/domains/tomato/tomics/alloc/validation/cross_dataset_scorecard.py` and `cross_dataset_gate.py` implement the multidataset scorecard/gate.
- `src/stomatal_optimiaztion/domains/tomato/tomics/alloc/validation/harvest_*` modules evaluate harvest-family behavior, promotion gates, mass balance, calibration bridge, and summaries.
- `src/stomatal_optimiaztion/domains/tomato/tomics/alloc/validation/rootzone_inversion.py` keeps KNU rootzone/EC data as bounded diagnostic evidence.
- `src/stomatal_optimiaztion/domains/tomato/tomics/alloc/components/partitioning/*` preserves the shipped `partition_policy: tomics` incumbent and research-only/promoted allocator variants.

## External Interfaces
- `configs/data/tomics_multidataset_candidates/traitenv_candidate_registry.json` is the public/school/competition candidate intake registry.
- `configs/data/knu_private_data_contract.template.yaml` documents the private KNU fixture contract without committing raw/private data.
- `configs/exp/tomics_multidataset_harvest_factorial_*.yaml` and `configs/exp/tomics_multidataset_harvest_promotion_gate_*.yaml` select public and mixed measured-harvest dataset sets.
- `tests/fixtures/knu_sanitized/*` provides small sanitized KNU smoke fixtures; larger KNU rootzone aligned fixtures remain local-only and ignored.
- `configs/plotkit/tomics/*` is the spec-first graph rendering surface for reusable TOMICS validation figures.

## Coupling / Hotspots
- Dataset runnable status is coupled across candidate config, dataset contracts, metadata scorecard output, and multidataset gate tests.
- KNU private/rootzone fixture paths must remain contract-driven and local-only; raw/private data must not be committed.
- Public proxy-derived dry-weight datasets must keep direct-vs-derived semantics visible in metadata and scorecard surfaces.
- RAH `.rah/` state is local control-plane state; it is ignored so stale issue-specific restart packets do not pollute source-control review.
