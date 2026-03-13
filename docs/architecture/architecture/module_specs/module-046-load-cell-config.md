# Module Spec 046: load-cell-data Config

## Purpose

Open the first bounded `load-cell-data` seam by porting the pipeline configuration surface that defines runtime defaults, path coercion, and YAML loading behavior.

## Source Inputs

- `load-cell-data/loadcell_pipeline/config.py`

## Target Outputs

- `src/stomatal_optimiaztion/domains/load_cell/config.py`
- `src/stomatal_optimiaztion/domains/load_cell/__init__.py`
- `src/stomatal_optimiaztion/domains/__init__.py`
- `tests/test_load_cell_config.py`

## Responsibilities

1. preserve the `PipelineConfig` dataclass default surface for load-cell preprocessing, thresholding, grouping, and flux options
2. preserve `to_dict()` path serialization and `load_config()` YAML/override behavior
3. open a canonical `domains/load_cell` package surface so later ingestion and workflow seams land on one import boundary

## Non-Goals

- migrate `loadcell_pipeline/io.py`
- migrate `loadcell_pipeline/preprocessing.py`
- widen into CLI, workflow, or dashboard entrypoints

## Validation

- `poetry run pytest`
- `poetry run ruff check .`

## Next Seam

- `load-cell-data/loadcell_pipeline/io.py`
