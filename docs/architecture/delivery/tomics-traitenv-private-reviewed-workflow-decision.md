# TOMICS traitenv private-reviewed workflow decision

## Problem statement

Issue `#265` now has a working private-reviewed derivative path for `school_trait_bundle__yield`, but the operational policy was still implicit.

The repository needed an explicit answer to this question:

- does `traitenv_school_validation` stay the official **manual-reviewed derivative workflow**
- or does it become an official **repo-local helper with guarded source-sync support**

This decision also had to stay separate from PR `#264`, which covers the lane-matrix architecture on another branch.

## Options considered

### Option A. Manual-reviewed derivative workflow

Pros:

- strongest provenance boundary
- easiest to explain in docs and PR text
- lowest risk of private-source leakage
- easiest to keep separate from public promotion semantics

Cons:

- more operator friction
- repeated sync/rebuild steps remain manual

### Option B. Repo-local helper with guarded source-sync support

Pros:

- more reproducible local operator flow
- less repeated setup friction
- easier to rerun from cloned private bundles

Cons:

- larger policy surface
- higher risk of blurring private derivative vs promotable public dataset
- would require stricter path and promotion guardrails than the current helper provides

## Decision

Choose **Option A** as the official repository workflow for this step.

The existing repo-local helper remains available, but only as a **bounded local preparation utility** for the manual-reviewed workflow.

That means:

- manual review remains the default provenance boundary
- the helper does not become the policy source of truth for promotion
- the committed public candidate registry remains conservative and review-only
- local helper outputs remain private-output artifacts, not public promotion evidence

## Why Option B is not chosen now

Option B was rejected for now because the current helper does not yet satisfy the stricter reading required for official source-sync automation.

Current gaps:

1. path recovery is not limited to explicit local paths or `.source_origin.json`; the helper still supports adjacent `outputs/traitenv` inference
2. `--approve-runnable-contract` can produce a locally runnable private overlay, which is acceptable for a bounded private workflow but is still too easy to misread as broader promotion widening
3. the branch still has heavy semantic overlap with PR `#264`, so formal source-sync promotion would further blur issue boundaries right before PR closure work

## Revisit criteria

Option B can be reconsidered only after all of the following are true:

1. raw workbook recovery is limited to explicit local path input or `.source_origin.json`
2. helper approval semantics are split clearly enough that private runnable preparation cannot be mistaken for public promotion eligibility
3. regression tests cover `.source_origin.json` recovery and the promotion-boundary contract
4. the issue `#265` branch is disentangled from PR `#264` overlap enough to open a clean workflow/productization PR

## Branch relation to PR #264

PR `#264` is a neighboring lane-matrix effort on branch `feat/263-add-tomics-lane-matrix-comparison-architecture`.

For this issue:

- do not treat PR `#264` as this branch's PR
- do not treat PR `#264` as this branch's merge signal
- if this branch keeps stacked local overlap, the future PR text must say that explicitly

## Immediate consequence

For the current branch closure pass, the smallest correct step is:

- document the manual-reviewed default
- keep the existing helper bounded and explicit
- strengthen provenance/test coverage around `.source_origin.json`
- prepare commit/push/PR-ready notes without claiming promotion widening
