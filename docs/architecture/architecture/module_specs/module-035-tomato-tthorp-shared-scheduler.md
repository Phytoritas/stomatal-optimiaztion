# Module Spec 035: TOMATO tTHORP Shared Scheduler

## Purpose

Open the next bounded TOMATO `tTHORP` seam by porting the shared scheduler helper layer that derives deterministic experiment keys and normalized run schedules from config payloads.

## Source Inputs

- `TOMATO/tTHORP/src/tthorp/core/scheduler.py`

## Target Outputs

- `src/stomatal_optimiaztion/domains/tomato/tthorp/core/`
- `tests/test_tomato_tthorp_core_scheduler.py`

## Responsibilities

1. preserve deterministic canonical hashing for experiment-key generation
2. preserve `RunSchedule` and config-derived `max_steps` / `default_dt_s` normalization
3. keep the shared scheduler surface package-local so downstream dayrun and script entrypoints can consume one migrated contract

## Non-Goals

- migrate `TOMATO/tTHORP/src/tthorp/pipelines/tomato_dayrun.py`
- migrate repo-level `scripts/run_pipeline.py`
- migrate repo-level `scripts/make_features.py`

## Validation

- `poetry run pytest`
- `poetry run ruff check .`

## Next Seam

- `TOMATO/tTHORP/src/tthorp/pipelines/tomato_dayrun.py`
