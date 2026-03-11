# Module Spec 000: Architecture Pipeline

## Purpose

Provide the control-plane workflow that turns the legacy source workspace into bounded refactor slices.

## Inputs

- legacy source inventory
- architecture decisions
- validation requirements

## Outputs

- audited source map
- ADRs
- module specs
- implementation checklists

## Responsibilities

1. identify the earliest failed architecture gate
2. convert uncertainty into explicit artifacts
3. define the next bounded migration slice
4. keep evidence linked to implementation work

## Non-Goals

- direct ownership of legacy runtime behavior
- bulk code import without prior boundary decisions
