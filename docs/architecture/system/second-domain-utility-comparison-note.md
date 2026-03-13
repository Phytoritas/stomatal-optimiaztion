# Second-Domain Utility Comparison Note

## Purpose

Decide whether the migrated repository now justifies a shared cross-domain utility layer.

## Domains Compared

### GOSM

- `domains/gosm/examples/control_figure.py`, `sensitivity_figures.py`, and `manuscript_panels.py` already needed a figure-bundle contract with CSV/spec/tokens/metadata exports plus fixed digest evidence.
- the original GOSM implementation kept that helper layer domain-local in `domains/gosm/examples/_plotkit.py`.

### THORP

- `domains/thorp/examples/figure_workflows.py` now reproduces five legacy MATLAB main-text figures and needs the same bundle contract as GOSM.
- `domains/thorp/examples/adapter.py` and `empirical.py` are still THORP-specific and should remain domain-local.

### Non-plotting domains

- `domains/tomato/tthorp/core/io.py`, `domains/load_cell/io.py`, and `domains/thorp/forcing.py` still solve domain-specific runtime or ETL contracts rather than cross-domain helper contracts.

## Comparison

1. The original "do not share utilities yet" decision stayed correct for runtime IO/config helpers, because those contracts still do not align across THORP, TOMATO, and `load_cell`.
2. The reopened example-parity wave created a new cross-domain overlap: both root `GOSM` and root `THORP` now need the same figure-bundle helper primitives for Plotkit-style exports.
3. That overlap is narrow and concrete. The shared concepts are only `FigureBundleArtifacts`, YAML loading, axis theming, output-path resolution, and frame digest hashing.

## Decision

Do not introduce a broad `src/stomatal_optimiaztion/shared/` package layer yet.

Introduce only a narrow shared plotting helper module, `src/stomatal_optimiaztion/shared_plotkit.py`, because the second domain has now crossed the reopen trigger with an identical figure-bundle contract.

Keep all non-plotting utility-like seams inside their domains until a second concrete reuse case appears without adapter glue or contract distortion.

## Reopen Trigger

Revisit a shared utility layer only if one of the following becomes true:

- a second non-plotting helper implementation is copied or reimplemented across two migrated domains
- a new cross-domain adapter repeatedly normalizes the same file/config contract
- the current shared plotting helper starts attracting unrelated config, IO, or runtime responsibilities
