# ADR-001: Finalize Staged Domain Package Shape

## Status

Accepted

## Context

The repository has completed bootstrap and audit work. Broad migration is still risky because the legacy workspace mixes several domains, caches, generated artifacts, and nested package layouts.

## Decision

Use a single Python package with staged domain subpackages:
- `stomatal_optimiaztion.domains.thorp`
- `stomatal_optimiaztion.domains.tomato`
- `stomatal_optimiaztion.domains.load_cell`

Migration rules:
- move one bounded seam at a time
- keep each seam independently testable
- copy only source assets needed by the active seam
- keep generated artifacts and large reference binaries out of Git unless they are explicitly approved fixtures

## Consequences

- the repo can hold shared architecture and migrated code without becoming a second umbrella dump
- the THORP domain becomes the first proving ground for the migration pattern
- shared abstractions stay blocked until at least two domains demonstrate the same need
