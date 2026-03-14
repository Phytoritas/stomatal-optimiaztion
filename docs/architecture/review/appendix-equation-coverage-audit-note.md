# Appendix Equation Coverage Audit Note

## Purpose

Record a document-only audit comparing the current root `THORP`, `GOSM`, and `TDGM` implementations against three literature appendices:

- `artifacts/papers/Potkay et al. - 2021 - Coupled whole-tree optimality and xylem hydraulics explain dynamic biomass partitioning-appendix.pdf`
- `artifacts/papers/Potkay et al. - 2022 - Turgor-limited predictions of tree growth, height and metabolic scaling over tree lifespans 1.pdf`
- `artifacts/papers/Potkay and Feng - 2023 - Do stomata optimize turgor-driven growth A new framework for integrating stomata response with whol_appendix.pdf`

This note distinguishes three cases that were easy to conflate during the refactor:

1. real missing runtime logic
2. appendix derivations that are folded into a later closed-form implementation
3. appendix future-work formulations that are documented but not part of the current executable model

## Scope

In scope:

- root `THORP`, `GOSM`, and `TDGM` runtime seams under `src/stomatal_optimiaztion/domains/`
- current architecture artifacts under `docs/architecture/`
- equation traceability via `@implements(...)`, module specs, and model-card JSON

Out of scope:

- TOMATO placeholder packages
- figure-only or plotting-only appendix scripts
- new code changes

## Summary

No new core runtime gap was found for root `THORP`.

No currently-open core runtime gap was found for root `GOSM`, but its appendix `S10.1-S10.2` branch should be interpreted as future-work support rather than as a missing part of the present executable model.

No currently-open core runtime gap was found for root `TDGM`, but part of the PTM appendix remains traceable only indirectly because several derivation-stage equations are absorbed into the later closed-form concentration solver instead of being exposed as standalone helpers.

The only still-open architecture/runtime issue visible after this audit remains the previously recorded long-horizon root `TDGM` parity drift, not a newly found missing appendix equation.

## Reading Rule

For this repository, appendix equations must be classified before calling them "missing":

- `Missing`: the paper uses the equation as part of the current model and no equivalent runtime logic exists.
- `Folded`: the paper shows the equation as an intermediate derivation, but the code implements a later equivalent closed form or decomposed final algorithm.
- `Future-work`: the appendix itself presents the formulation as a more complex extension rather than part of the current production model.

## THORP

### Verdict

Root `THORP` has no new missing runtime equation or algorithm relative to the 2021 appendix.

### Reasoning

- The current runtime covers the root-uptake, stomatal, growth, soil, and radiation seams already called out by the earlier MATLAB parity audit.
- The 2021 appendix `S4.1-S4.6` stem-conductance equations are derivation steps that lead to the executable `S4.7-S4.8` form.
- The current `stomata()` implementation computes `k_sw_max` directly from the final `S4.7` form and its diameter derivative from `S4.8`, so the earlier proportionality steps are folded rather than omitted.

### Evidence

- `docs/architecture/review/matlab-source-parity-audit-note.md` records no core `THORP` runtime gap.
- `src/stomatal_optimiaztion/domains/thorp/hydraulics.py` implements root uptake and stomatal optimization, including the final stem-conductance scaling.
- `src/stomatal_optimiaztion/domains/thorp/growth.py` implements the growth update used by the current runtime.

### Interpretation

If strict appendix traceability is desired, `S4.1-S4.6` could be documented as derivation-only ancestors of the current `k_sw_max` calculation, but this is not a runtime gap.

## GOSM

### Verdict

Root `GOSM` has no currently-open core runtime gap against the present 2023 executable model.

### Reasoning

- The one bounded helper previously missing from the older parity wave, `FUNCTION_Solve_mult_phi_given_assumed_NSC.m`, is now present as `solve_mult_phi_given_assumed_nsc(...)`.
- The present runtime pipeline still executes the steady-state `S3-S6` path, which matches the current GOSM formulation.
- Appendix `S10.1-S10.2` is explicitly introduced as "a more complex model formulation for future development", so lack of full runtime integration there should not be treated as a missing present-day kernel.

### Evidence

- `docs/architecture/review/matlab-source-parity-audit-note.md` records the old helper gap and notes that it was later closed by slice `094`.
- `src/stomatal_optimiaztion/domains/gosm/model/steady_state.py` now contains `solve_mult_phi_given_assumed_nsc(...)`.
- `src/stomatal_optimiaztion/domains/gosm/model/pipeline.py` still exposes the current executable `S3-S6` pipeline.
- `src/stomatal_optimiaztion/domains/gosm/model/future_work.py` contains helper-level implementations for `Eq.S10.1` and `Eq.S10.2`.
- `src/stomatal_optimiaztion/domains/gosm/model_card/C009.json` explicitly frames `S10.2` as future development and notes unresolved definitions for the full `F_i` dynamics.

### Interpretation

`GOSM` currently sits in a mixed state:

- present model: implemented
- future-work branch: partially represented as helpers and documentation, not as a full runtime branch

That is acceptable unless the project goal changes from parity with the published current model to prototyping the future complex formulation.

## TDGM

### Verdict

Root `TDGM` has no currently-open core runtime gap, but it retains one documentation-grade traceability weakness.

### Reasoning

- The bounded compatibility helper previously missing from the MATLAB parity audit, `FUNCTION_Initial_Mean_Allocation_Fractions.m`, is now implemented as `initial_mean_allocation_fractions(...)`.
- The turgor-driven growth core (`S2.12`, `S2.16`) and THORP-G coupling core (`S3.1-S3.8`) are present.
- The PTM front-half derivations in `S1.9-S1.21` are not exposed as standalone runtime helpers. Instead, the current PTM seam exposes the later closed-form concentration solver (`Eq_S1.26`, `Eq_S1.30`, `Eq_S1.35`, `Eq_S1.36`, `Eq_S1.38`) and folds earlier unloading/flux derivations into the coefficients of that solver.

### Evidence

- `docs/architecture/review/matlab-source-parity-audit-note.md` records the old allocation-memory initialization gap and notes that it was later closed by slice `095`.
- `src/stomatal_optimiaztion/domains/tdgm/coupling.py` now contains `initial_mean_allocation_fractions(...)`, `realized_growth_rate(...)`, and the allocation-memory filter.
- `src/stomatal_optimiaztion/domains/tdgm/turgor_growth.py` implements `Eq_S2.12` and `Eq_S2.16`.
- `src/stomatal_optimiaztion/domains/tdgm/ptm.py` exposes the closed-form PTM concentration solver but not separate helpers for `S1.9-S1.21`.
- `src/stomatal_optimiaztion/domains/tdgm/model_card/C002.json` still documents `Eq_S1.9-S1.21`, so the literature traceability is richer than the current public helper surface.

### Interpretation

This is not a proof of wrong behavior. It means:

- runtime parity target: mostly satisfied
- appendix-to-function 1:1 traceability: incomplete for PTM derivation steps

If a future documentation or pedagogy slice wants exact paper-to-code correspondence, the best candidate is a bounded TDGM PTM documentation/helper slice that re-exposes `S1.9-S1.21` as named intermediate helpers without changing numerical behavior.

## Cross-Model Difference In Plain Language

- `THORP`: mostly "folded, not missing"
- `GOSM`: mostly "future-work, not required for current runtime"
- `TDGM`: mostly "implemented, but some derivation steps are folded together"

## Open Risk After This Audit

The only still-open item that remains actionable at the architecture level is:

- root `TDGM` long-horizon control drift against the legacy MATLAB payload, already recorded as `D-108` in `docs/architecture/gap_register.md`

This audit did not find evidence that the drift is caused by a newly discovered missing appendix equation.

## Verification Snapshot

Targeted regression checks used during the audit:

- `.venv\\Scripts\\python.exe -m pytest tests/test_gosm_steady_state_inversion.py tests/test_tdgm_coupling.py tests/test_thorp_equation_registry.py -q`

Result:

- `9 passed`

## Recommended Next Step

Do not open a new runtime refactor wave from these appendix notes alone.

If a follow-up documentation slice is desired, prefer one of the following:

1. add a small TDGM PTM traceability note or helper-spec for `S1.9-S1.21`
2. add a GOSM note that explicitly separates current-model equations from `S10` future-work equations
3. keep the repository in monitor mode and treat the appendix audit as informational evidence only
