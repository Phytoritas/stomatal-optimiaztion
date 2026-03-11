# ADR-000: Adopt Recursive Architecture Workflow

## Status

Accepted

## Context

The new `stomatal-optimiaztion` repository exists to support staged refactoring of a larger legacy workspace. Starting implementation before an architecture baseline would create avoidable churn.

## Decision

Adopt a recursive architecture workflow:
- bootstrap scaffold first
- audit the source workspace before code migration
- use ADRs and module specs to define bounded slices
- block broad implementation until the implementation gate is satisfied

## Consequences

- documentation is a first-class artifact in this repository
- early velocity is directed toward clarity rather than bulk code movement
- migration progress is easier to validate and review
