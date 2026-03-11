# Workspace Audit

## Bound Context

- Bound repo root: `C:\Users\yhmoo\OneDrive\Phytoritas\projects\stomatal-optimiaztion`
- Legacy source root: `C:\Users\yhmoo\OneDrive\Phytoritas\00. Stomatal Optimization`
- Audit date: 2026-03-12

## Repo Profile Inference

Target repo profile:
- python refactoring workspace
- architecture-first migration repo
- likely multi-domain or staged monorepo target

Legacy source profile:
- umbrella folder containing multiple Python subprojects and generated artifacts
- not yet aligned to the workspace factory scaffold as one coherent repository

## Observed Legacy Top Level

- `THORP`: Python package repo with `src`, `tests`, `docs`, `scripts`, `data`, `example`, and `model_card`
- `TOMATO`: umbrella tree containing `tTHORP`, `tGOSM`, `tTDGM`, plus integration docs and output artifacts
- `load-cell-data`: separate pipeline-oriented Python project with preprocessing and visualization outputs
- `.venv`, `.pytest_cache`, `.codex-home`, and generated outputs exist inside the legacy workspace and should not be treated as migration sources

## Initial Structural Findings

1. The legacy source is already split into domain-oriented subprojects, but the umbrella folder mixes source, tooling, caches, and generated artifacts.
2. `THORP` appears closest to a modern single-package layout and can serve as the first reference domain for boundary design.
3. `TOMATO` contains nested packages and integration tests, which suggests future migration work needs explicit cross-package contracts.
4. `load-cell-data` behaves more like a pipeline project than a model-core package and may need its own adapter boundary.

## Early Risks

- generated outputs and caches may be copied into the new repo accidentally
- duplicated concepts across `THORP`, `TOMATO`, and `load-cell-data` may create naming drift
- nested package layouts inside `TOMATO` can blur migration boundaries
- validation commands for the umbrella folder are not yet normalized in this new repo

## Earliest Failed Gate

Current earliest failed gate: target architecture selection

Reason:
- the scaffold exists, but the target decomposition for the new repository is not yet explicit

## Recommended First Slice

Start with a design-only slice:
- map `THORP` as the first candidate source domain
- define whether the new repo should host extracted packages or only orchestration and migration docs
- specify the first smoke and regression hooks before moving code
