# Module Spec 037: TOMATO tTHORP Repo-Level Pipeline Script

## Purpose

Open the next bounded TOMATO `tTHORP` seam by porting the repo-level pipeline runner script that executes YAML-configured runs, writes deterministic artifacts, and prints a stable JSON summary for automation.

## Source Inputs

- `TOMATO/tTHORP/scripts/run_pipeline.py`

## Target Outputs

- `scripts/run_pipeline.py`
- `tests/test_tomato_tthorp_run_pipeline_script.py`

## Responsibilities

1. preserve CLI argument parsing for config path, output-dir override, and explicit experiment-key override
2. preserve deterministic CSV and metrics-JSON artifact naming over migrated package seams
3. preserve printed JSON summary shape so shell automation can consume the runner output

## Non-Goals

- migrate `TOMATO/tTHORP/scripts/make_features.py`
- broaden into non-TOMATO repo-level automation entrypoints
- rework the migrated package-level dayrun orchestration surface

## Validation

- `poetry run pytest`
- `poetry run ruff check .`

## Next Seam

- `TOMATO/tTHORP/scripts/make_features.py`
