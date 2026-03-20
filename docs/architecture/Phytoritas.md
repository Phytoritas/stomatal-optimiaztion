# Phytoritas Blueprint

## Boundaries

- Bound repo root: `C:\Users\yhmoo\OneDrive\Phytoritas\projects\stomatal-optimiaztion`
- Legacy source root: `C:\Users\yhmoo\OneDrive\Phytoritas\00. Stomatal Optimization`
- Working mode: auto-bootstrap plus manual evidence capture
- Current phase: the recursive architecture refactoring wave is closed, including the former root `TDGM` later-horizon control gap `D-108`; the architecture spine and validation contract are green, continuous root `TDGM` parity is exact through day `784.5`, the shipped post-day-`791.5` control reopening is now recorded as a reference-payload resume artifact in `docs/architecture/review/tdgm-reference-payload-resume-provenance-note.md`, the TOMICS naming and first hybrid tomato partition-policy slice is complete through issue `#227` / module `114`, the TOMICS-Alloc research-only architecture pipeline is complete through issue `#231` / module `115`, and issue `#233` / module `116` now standardizes reusable repo-local graph rendering on Plotkit spec bundles with the live TOMICS figure scripts migrated onto that contract

## Scope

Create a scaffold-aligned refactoring program for the legacy "00. Stomatal Optimization" workspace without starting broad code migration yet.

The initial scope covers:
- source inventory across `THORP`, `GOSM`, `TDGM`, `TOMATO`, and `load-cell-data`
- target module boundary proposal for the new repository
- validation and regression harness planning
- migration slice planning for the first bounded implementation wave

The initial scope excludes:
- full code import
- large-scale renames inside legacy repositories
- behavior-changing model edits without explicit validation packets

## Phase Goals

### Phase 0. Bootstrap
- create the new repository scaffold
- seed architecture artifacts
- record source and target paths

### Phase 1. Audit
- inventory the legacy workspace structure
- identify active subprojects, duplicated concepts, and generated artifacts
- record the earliest failed gate

### Phase 2. Boundary Design
- decide whether the new repo should be a monorepo, domain package, or staged migration repo
- define target modules, interfaces, and migration seams
- create ADRs and module specs before implementation

### Phase 3. Validation Design
- define smoke, regression, and naming checks
- map validation targets to source subprojects and target packages
- identify must-keep artifacts and must-ignore artifacts

### Phase 4. Bounded Refactor
- execute one migration slice at a time
- keep each slice tied to an ADR, module spec, and verification step
- avoid multi-domain changes in one batch

### Phase 5. Review And Hardening
- update design records
- review regression results
- prepare the next slice

## Decision Gates

### Gate A. Source Audit Complete
Required evidence:
- top-level source inventory
- identified subprojects
- generated artifact inventory

### Gate B. Target Architecture Chosen
Required evidence:
- system brief
- at least one ADR
- first module spec

### Gate C. Validation Plan Ready
Required evidence:
- implementation gate checklist
- named smoke and regression commands
- migration risk list

### Gate D. First Slice Approved
Required evidence:
- bounded scope
- affected files list
- rollback strategy

Broad implementation remains blocked until Gates A through C are satisfied.

## Recursive Improvement Cycle

1. audit the current source and identify the earliest unresolved architectural uncertainty
2. convert that uncertainty into a document, checklist, or experiment
3. choose the smallest next slice that reduces structural ambiguity
4. validate the slice with tests, logs, or output artifacts
5. record the delta and open the next loop

## Verification Loops

- structure loop: directory and package boundary checks
- behavior loop: smoke and regression tests
- naming loop: variable glossary alignment and legacy alias mapping
- documentation loop: ADRs, module specs, and change records

## Immediate Next Actions

1. treat the current architecture scaffold, ADR spine, module-spec chain, and rerun parity bundle contract as the stable baseline for further work
2. keep the validation gates green by rerunning the fast root parity tests and `scripts/render_root_rerun_parity_figures.py --fast-smoke` whenever `THORP`, `GOSM`, or `TDGM` runtime kernels change
3. rerender the default full-series control bundles for root `THORP` and `TDGM` whenever their runtime kernels change so the canonical `python/legacy/diff` CSV evidence stays current
4. use `docs/architecture/review/tdgm-reference-payload-resume-provenance-note.md` as the source of truth if later-horizon shipped `TDGM` control diffs are revisited
5. keep the shipped `tomics` path stable and use issue `#231` / module `115` to evaluate only opt-in TOMICS-Alloc research architectures against the local tomato primary-source corpus before any future default promotion
6. keep reusable graphs on the Plotkit spec-first path and update the saved TOMICS specs under `configs/plotkit/tomics/` whenever live tomato figure structure changes
