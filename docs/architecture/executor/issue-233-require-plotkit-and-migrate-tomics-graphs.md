## Why
- The repo already had a partial Plotkit-style figure contract for root rerun parity, but the live TOMICS graph scripts still rendered from ad-hoc `matplotlib` code.
- Reusable validation figures need the same spec/tokens/metadata bundle contract across compare, factorial, and tomato plotting helpers.
- Future graph work in this repo should default to `$plotkit-publication-graphs` rather than one-off chart code.

## Affected model
- repo-local graph-rendering workflow
- TOMICS compare/factorial/simulation/allocation plotting surfaces
- Plotkit specs under `configs/plotkit/tomics/`

## Validation method
- targeted TOMICS plotting tests
- TOMICS compare/factorial/architecture runner tests
- TOMICS runners re-executed end to end
- `poetry run pytest`
- `poetry run ruff check .`

## Comparison target
- existing root rerun parity Plotkit-style bundles
- previous TOMICS direct `matplotlib` outputs
