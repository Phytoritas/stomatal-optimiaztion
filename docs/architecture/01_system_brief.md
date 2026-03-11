# System Brief

## Problem Statement

The legacy "00. Stomatal Optimization" folder contains valuable model and pipeline work, but it is organized as an umbrella workspace rather than a single scaffold-aligned refactoring repository.

The new `stomatal-optimiaztion` repo exists to provide:
- a stable architecture workspace
- a migration-friendly documentation backbone
- a clean place to stage bounded refactor slices

## Candidate Target Shape

Short term:
- keep this repo as the architecture and migration control plane
- defer broad source import
- define contracts and destination modules before copying code

Probable medium-term shape:
- `src/stomatal_optimiaztion/domains/thorp`
- `src/stomatal_optimiaztion/domains/tomato`
- `src/stomatal_optimiaztion/domains/load_cell`
- `configs/` for migration and experiment settings
- `docs/architecture/` for decisions and evidence

## Primary Source Domains

### THORP
- model-oriented Python package
- includes equations, forcing, hydraulics, growth, and simulation modules
- likely best first candidate for source mapping

### TOMATO
- nested package workspace with `tTHORP`, `tGOSM`, and `tTDGM`
- includes integration tests, configs, and output artifacts
- likely requires explicit interface and package boundary decisions

### load-cell-data
- preprocessing and analysis pipeline
- includes CLI and visualization-oriented outputs
- should likely remain separated from model-core packages through adapters or data contracts

## Architectural Principle

Refactor by boundary and evidence, not by bulk copying. The new repo should only absorb code after:
- module boundaries are named
- validation commands are defined
- artifact handling rules are explicit

## Immediate Deliverables

1. define the target repo profile
2. define the first migration seam
3. define verification commands for the first seam
