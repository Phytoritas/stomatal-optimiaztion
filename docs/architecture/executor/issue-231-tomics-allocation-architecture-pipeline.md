## Why
- The live TOMICS-Alloc default is stable and greenhouse-safe, but it still represents only the first bounded hybrid allocation layer.
- The repository needs a primary-source, equation-traceable architecture study across TOMSIM, TOMGRO, De Koning, Vanthoor, and Kuijpers to decide the next tomato-first allocation architecture.
- The current shipped default must remain unchanged while reserve/buffer, fruit-feedback, and richer fruit/vegetative structure are screened as opt-in research variants only.

## Affected model
- `TOMICS-Alloc`
- tomato allocation research seams under `src/stomatal_optimiaztion/domains/tomato/tomics/alloc/components/partitioning/`
- `tomato_legacy` pipeline integration points
- staged architecture-study outputs under `out/tomics/analysis/allocation-factorial/`

## Validation method
- targeted architecture-study tests
- current TOMICS regression tests
- current compare runner and current screening factorial reruns
- new architecture factorial runner
- `poetry run pytest`
- `poetry run ruff check .`

## Comparison target
- current shipped TOMICS default
- TOMSIM-informed storage candidate
- De Koning canopy-demand candidate
- Vanthoor greenhouse-buffer candidate
- TOMGRO feedback candidate
- Kuijpers common-structure hybrid candidate
- bounded THORP root-correction variants only as subordinate greenhouse corrections
