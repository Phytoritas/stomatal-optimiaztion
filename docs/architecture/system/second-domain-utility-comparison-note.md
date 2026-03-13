# Second-Domain Utility Comparison Note

## Purpose

Decide whether the migrated repository now justifies a shared cross-domain utility layer.

## Domains Compared

### THORP

- `domains/thorp/forcing.py` is a domain runtime seam that reconstructs solar-angle and repeated forcing fields from THORP-specific netCDF structure.
- `domains/thorp/matlab_io.py` is a legacy MATLAB compatibility seam tied to THORP output contracts.
- `domains/thorp/params.py` is a flat physiology/config compatibility surface for THORP callers.

### TOMATO tTHORP

- `domains/tomato/tthorp/core/io.py` handles config inheritance, YAML loading, JSON metadata emission, and output-directory setup for TOMATO pipelines.
- `domains/tomato/tthorp/core/util_units.py` is a very small PAR conversion utility scoped to TOMATO feature building.

### load_cell

- `domains/load_cell/config.py` is a pipeline-config loader for CSV preprocessing and event-detection parameters.
- `domains/load_cell/io.py` is a pandas-heavy ingestion/output seam for 1-second reindexing, interpolation flags, and multi-resolution artifact writing.

## Comparison

1. The names overlap at a superficial level, but the contracts do not. THORP `forcing.py` and TOMATO `core/io.py` both touch files, yet one is model-runtime forcing reconstruction and the other is pipeline-config orchestration.
2. The dependencies do not align. THORP utility-like seams are built around `netCDF4`, `scipy.io`, and physiological parameter objects, while `load_cell` utilities are pandas-centered ETL seams and TOMATO utilities are YAML/JSON pipeline helpers.
3. The reuse pressure is still weak. Only TOMATO currently needs `ensure_dir` and config merge helpers; only load-cell needs tabular multi-resolution writers; only THORP needs MATLAB and forcing compatibility layers.

## Decision

Do not introduce `src/stomatal_optimiaztion/shared/` yet.

Keep utility-like seams inside their current domains until at least one concrete helper is used by two migrated domains without adapter glue or contract distortion.

## Reopen Trigger

Revisit a shared utility layer only if one of the following becomes true:

- the same helper implementation is copied or reimplemented across two migrated domains
- a new cross-domain adapter repeatedly normalizes the same file/config contract
- tests start requiring duplicate fixtures or assertions for one identical helper concept
