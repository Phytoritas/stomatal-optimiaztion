# TOMICS Allocation Primary Source Review

## Scope

This review covers the exact local tomato primary-source corpus used for the next TOMICS-Alloc architecture study.

Secondary THORP-family sources were consulted only after the tomato-first corpus had been reviewed.

## Review status by source family

| Source family | Local file | Review extent | Direct source claims carried forward | Exact equations / algorithms reviewed | Validity domain and warnings |
|---|---|---|---|---|---|
| TOMSIM / Heuvelink | `Heuvelink - 1996 - Tomato growth and yield quantitative analysis and synthesis.pdf` | Partial full-text review: Ch. 5.2, 5.5, 5.7, 6.1 | One common assimilate pool for tomato fruit and vegetative sinks; relative sink-strength partitioning; explicit critique of TOMGRO storage omission; canopy/LAI control matters in greenhouse tomato | Relative sink partition logic, constant vegetative sink baseline, storage-pool rationale, Richards/Gompertz truss-growth references | Greenhouse tomato thesis context; do not over-transfer to non-greenhouse or non-tomato domains |
| TOMGRO / Jones et al. | `J. W. Jones et al. - 1991 - A DYNAMIC TOMATO GROWTH AND YIELD MODEL (TOMGRO).pdf` | Full text reviewed | Age-structured organs, demand/supply limiter, Rc scaling, SLA-driven leaf-demand path, daily plus faster subdaily logic | Eq. (4) through Eq. (24), especially demand, supply, maintenance respiration, and Rc-limited growth | Original calibration is not a greenhouse-long-crop universal law; no explicit carry-over reserve pool; SLA-as-driver is risky for shipped default |
| De Koning | `De Koning - 1994 - Development and dry matter distribution in glasshouse tomato  a quantitative approach.pdf` | Partial full-text review: conceptual structure, fruit-growth, crop-control, long-run greenhouse reasoning | Partitioning proportional to potential growth rates; vegetative unit concept; fruit-load and sink-formation logic; fruit-production optimum near LAI 2-3 | Vegetative-unit framing, potential fruit-growth/Gompertz structure, Eq. 8.2.4 crop-growth identity | Glasshouse tomato crop-control framing; roots are not the dominant modeled above-ground sink logic |
| Vanthoor article | `Vanthoor et al. - 2011 - A methodology for model-based greenhouse design Part 2, description and validation of a tomato yiel 1.pdf` | Partial article review | Greenhouse state-flow rigor, medium-grained organ architecture, validation framing | Article narrative around model structure and validation | Use article for architecture context; use appendix for exact equations |
| Vanthoor appendix | `Vanthoor - 1 Electronic appendix of the manuscript entitled A 2 methodology for model-based greenhouse design.pdf` | Appendix and equations reviewed | Explicit carbohydrate buffer, temperature-sum gating, fixed boxcar fruit stages, maintenance respiration gates, pruning at maximum LAI | Eq. (1) through Eq. (47), especially `CBuf`, temperature-sum, fruit stage train, buffer gates, maintenance, pruning | Strong greenhouse relevance, but stem/root lumping and full buffer coupling are too invasive for silent promotion to shipped default |
| Kuijpers | `Kuijpers et al. - 2019 - Model selection with a common structure Tomato crop growth models.pdf` | Full text reviewed | Common-structure architecture and model-selection logic; component interchange is not automatically valid; non-identifiability warning | Common structure Eq. (3) and Eq. (5), process-block decomposition | Architecture scaffold only; not a direct tomato physiology replacement |

## Secondary source use after tomato corpus

| Source family | Local file | Review extent | Accepted use | Explicit non-use |
|---|---|---|---|---|
| THORP / Potkay 2021 | `Potkay et al. - 2021 - Coupled whole-tree optimality and xylem hydraulics explain dynamic biomass partitioning.pdf` | Targeted partial review after tomato sources | Bounded greenhouse root-correction proxy only | Not used as a master whole-plant tomato allocator |
| TDGM / GOH related sources | `Potkay et al. - 2022 ...`, `Potkay and Feng - 2023 ...` | Targeted partial review after tomato sources | Reserve, maintenance, and dynamic-coupling ideas for future seams | Not used to override tomato-first allocation structure in this slice |

## Direct claims vs synthesis vs inference

Direct claims from source:
- Heuvelink supports a tomato-first common assimilate pool with sink-strength partitioning.
- De Koning and greenhouse crop-control reasoning support canopy preservation rather than maximizing short-run fruit draw.
- Vanthoor supplies the exact greenhouse carbohydrate-buffer equations.
- Kuijpers explicitly warns that components are not automatically modular after calibration.

Comparative synthesis:
- The tomato-first sources agree that fruit-vs-vegetative competition should remain a shared-pool tomato problem.
- Vanthoor offers the strongest exact greenhouse buffer formalism, while Heuvelink provides the clearest tomato-first rationale for allowing reserve carry-over.
- De Koning contributes the best explicit greenhouse tomato argument for vegetative demand structure and LAI control.

Inference:
- A reduced storage seam is safer than directly adopting the full Vanthoor buffer in the next shipped architecture.
- Fruit-abortion feedback is worth screening, but not worth promoting into shipped default without tomato-regime validation in the current pipeline.
- THORP-derived logic remains structurally secondary in greenhouse tomato.

## Key review conclusions

1. The shipped default should remain greenhouse-safe, tomato-first, and fruit-anchor preserving.
2. The first architecture seam worth screening beyond the shipped default is an explicit reserve/buffer seam.
3. The safest first reserve/buffer candidate is TOMSIM-like carry-over storage, not a full Vanthoor buffer promotion.
4. De Koning vegetative-demand structure is the strongest candidate to enrich the next architecture without abandoning tomato logic.
5. TOMGRO fruit-feedback and SLA-driver ideas should remain research-only.
