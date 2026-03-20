# Phytoritas

Canonical blueprint: [docs/architecture/Phytoritas.md](docs/architecture/Phytoritas.md)

This repository is the scaffold-first refactoring workspace for the legacy source tree at:

`C:\Users\yhmoo\OneDrive\Phytoritas\00. Stomatal Optimization`

Current status:
- Bootstrap complete
- Architecture scaffold seeded
- Target repo shape finalized as a staged single-package domain workspace
- Slices 001-024 migrated: THORP bounded runtime, reporting, config, IO, and CLI seams
- Slices 025-045 migrated: TOMATO `TOMICS-Alloc` contracts, interface, forcing, adapters, `TomatoModel`, runner, partitioning-package, package-level legacy pipeline, shared IO, shared scheduler, dayrun pipeline, repo-level scripts, feature-builder script, THORP reference adapter, plotting seams, plus `TOMICS-Flux` and `TOMICS-Grow` contract/interface seams
- Slice 046 migrated: `load-cell-data` config seam
- Slice 047 migrated: `load-cell-data` IO seam
- Slice 048 migrated: `load-cell-data` aggregation seam
- Slice 049 migrated: `load-cell-data` threshold-detection seam
- Slice 050 migrated: `load-cell-data` preprocessing seam
- Slice 051 migrated: `load-cell-data` event-detection seam
- Slice 052 migrated: `load-cell-data` flux-decomposition seam
- Slice 053 migrated: `load-cell-data` pipeline CLI seam
- Slice 054 migrated: `load-cell-data` workflow seam
- Slice 055 migrated: `load-cell-data` sweep seam
- Slice 056 migrated: `load-cell-data` end-to-end runner seam
- Slice 057 migrated: `load-cell-data` raw ALMEMO preprocessing seam
- Slice 058 migrated: `load-cell-data` synthetic validation harness seam
- Slice 059 migrated: `load-cell-data` real-data benchmark harness seam
- Slice 060 migrated: `load-cell-data` incremental preprocess harness seam
- Slice 061 migrated: `load-cell-data` preprocess-compare local server seam
- Slice 062 migrated: `load-cell-data` static preprocess-compare viewer seam
- Slice 063 migrated: THORP stable `sim` runner seam
- Slice 064 migrated: THORP equation-registry seam
- Slice 065 migrated: THORP utilities namespace seam
- Slice 066 migrated: THORP IO namespace seam
- Slice 067 migrated: THORP model namespace seam
- Slice 068 migrated: THORP params compatibility seam
- Slice 069 recorded: THORP package-level smoke validation note
- Slice 070 recorded: second-domain utility comparison note
- Slice 071 migrated: root GOSM model-card and traceability foundation
- Slice 072 migrated: root TDGM model-card and traceability foundation
- Slice 073 migrated: root GOSM parameter-defaults seam
- Slice 074 migrated: root GOSM radiation kernel seam
- Slice 075 migrated: root GOSM allometry helper seam
- Slice 076 migrated: root GOSM NPP/GPP helper seam
- Slice 077 migrated: root GOSM optimal-control helper seam
- Slice 078 migrated: root GOSM carbon-dynamics helper seam
- Slice 079 migrated: root GOSM conductance-temperature kernel
- Slice 080 migrated: root GOSM carbon-assimilation kernel
- Slice 081 migrated: root GOSM math helper seam
- Slice 082 migrated: root GOSM hydraulics kernel
- Slice 083 migrated: root GOSM runtime pipeline seam
- Slice 084 migrated: root GOSM future-work helper seam
- Slice 085 migrated: root GOSM stomatal-model comparison seam
- Slice 086 migrated: root GOSM instantaneous optimum seam
- Slice 087 migrated: root GOSM steady-state helper seam
- Slice 088 migrated: root TDGM turgor-driven growth seam
- Slice 089 migrated: root TDGM phloem-transport seam
- Slice 090 migrated: root TDGM coupling seam
- Slice 091 migrated: root TDGM equation-registry seam
- Slice 092 migrated: root TDGM THORP-G postprocess seam
- Slice 093 recorded: MATLAB source parity audit for root THORP, GOSM, and TDGM
- Slice 094 migrated: root GOSM steady-state inversion helper
- Slice 095 migrated: root TDGM initial mean-allocation helper
- Slice 096 recorded: legacy example and figure parity audit for root THORP, GOSM, and TDGM
- Slice 097 migrated: root GOSM control example figure workflow
- Slice 098 migrated: root GOSM sensitivity and manuscript figure workflows
- Slice 099 migrated: root THORP main-text example figure workflows plus a narrow shared Plotkit bundle helper
- Slice 100 migrated: root TDGM supplementary offline and THORP-G example figure workflows with Plotkit-style figure bundles
- Slice 101 migrated: TOMICS-Alloc architecture-study seams, source-traceable reserve/buffer and feedback helpers, and staged architecture factorial runner
- Active bounded slice: issue `#231` / module `115` extends TOMICS-Alloc with a primary-source architecture pipeline and research-only candidate screening while keeping the shipped `tomics` default unchanged
- Current open architecture gap: none
