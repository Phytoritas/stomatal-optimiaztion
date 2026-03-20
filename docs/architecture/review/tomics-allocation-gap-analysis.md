# TOMICS Allocation Gap Analysis

## Comparison set

| Candidate | Fruit law | Vegetative demand | Reserve / buffer | Fruit structure | Fruit feedback | Root representation | SLA role | Greenhouse relevance | Integration cost | Recommendation |
|---|---|---|---|---|---|---|---|---|---|---|
| Current shipped TOMICS default | Legacy sink exact | Constant whole-crop | Off | Truss cohort proxy in existing model | Off | Bounded explicit root | Derived / observational | High | Low | Keep shipped now |
| TOMSIM-informed candidate | Legacy sink exact | Constant whole-crop | Reduced storage seam | Truss cohort | Off | Bounded explicit root | Derived / observational | High | Medium | Strong first reserve candidate |
| TOMGRO-informed candidate | Rc-limited or feedback proxy | Dynamic age demand | Off | Age classes | Abort proxy | Implicit small root | Independent driver | Medium | Medium | Research-only |
| De Koning-informed candidate | Potential-growth competition over common pool | Vegetative unit | Off | Fruit-load / potential-growth emphasis | Source-demand proxy | Bounded explicit root | Derived / observational | High | Medium | Strong canopy-demand candidate |
| Vanthoor-informed candidate | Buffer-mediated organ flows | Medium-grained organ flows | Explicit `CBuf` | Fixed boxcar train | Fruit-set gates | Stem/root lump | Empirical greenhouse links | High in greenhouse, but coupled | High | Research-only |
| Kuijpers hybrid candidate | Legacy sink exact | De Koning vegetative unit | Reduced TOMSIM-like storage seam | Existing truss cohort retained | Off | Bounded hysteretic root correction | Derived / observational | High | Medium | Best next architecture target |
| Recommended next shipped architecture | Not yet promoted | Not yet promoted | Not yet promoted | Not yet promoted | Not yet promoted | Not yet promoted | Not yet promoted | n/a | n/a | Keep shipped default; graduate only after calibration |

## What remains in shipped default now

- legacy fruit anchoring
- bounded greenhouse root correction
- LAI-band canopy governor
- no explicit reserve/buffer seam
- no fruit-abortion or fruit-set feedback

## What becomes research-only

- TOMSIM-like storage seam
- full Vanthoor-like carbohydrate buffer
- TOMGRO fruit-abortion proxy
- De Koning source-demand fruit feedback
- TOMGRO independent SLA driver
- Vanthoor fixed boxcar fruit train
- THORP hysteretic correction modes

## What belongs in Alloc vs Grow vs a buffer seam

Belongs in Alloc:
- fruit-vs-vegetative partition law
- greenhouse-safe root moderation
- canopy governor
- research-only architecture toggles for fruit structure and vegetative-demand mode

Belongs in Grow:
- detailed maintenance respiration closure once it becomes a stable physiology commitment
- fruit stage biomass accumulation beyond the current allocation proxy layer

Belongs in a dedicated buffer seam:
- TOMSIM-like storage carry-over
- Vanthoor-like carbohydrate buffer accounting
- any day/night decoupling that should not silently alter the shipped default

## What belongs in phenology or fruit-set rather than Alloc

- full fruit-set and abortion dynamics
- temperature-sum transitions between vegetative and generative stages
- fixed boxcar train stage transitions

These can influence allocation, but they should not be hidden inside the stable TOMICS allocation default.

## THORP should continue to do

- provide bounded hydraulic/root correction signals
- increase root allocation only under greenhouse stress and only within caps
- remain subordinate to tomato sink logic

## THORP must not do

- become the direct master whole-plant tomato allocator
- override fruit anchoring
- import deep-soil or tree-root assumptions as greenhouse defaults

## Reserve / buffer recommendation

Reserve/buffer should remain research-only for now.

Recommendation:
- screen a reduced TOMSIM-like storage seam first
- keep the full Vanthoor buffer as a later greenhouse-research path

Reason:
- storage gives the architecture a tomato-first carry-over seam
- the full Vanthoor buffer is exact and valuable, but materially more coupled to greenhouse state-flow design

## Fruit-abortion recommendation

Fruit abortion should remain research-only.

Reason:
- tomato literature supports source-demand fruit-load feedback as a valid research mechanism
- but the current pipeline does not yet have enough phenology and calibration support to promote it into shipped default

## Vegetative-unit logic recommendation

De Koning vegetative-unit logic should be explicit in research mode and approximate in future promotion work.

Short version:
- explicit for research screening
- not yet mandatory in shipped default

## Vanthoor stem/root lump recommendation

Vanthoor stem/root lumping should be mapped, not preserved as the future shipped default.

Reason:
- it is a legitimate medium-grained greenhouse representation
- but current TOMICS-Alloc already exposes explicit root moderation, so regressing to a permanent lump would lose interpretability

## Structural differences worth screening factorially

- reserve/buffer off vs storage vs full greenhouse buffer
- constant vegetative demand vs De Koning vegetative unit vs TOMGRO dynamic age
- truss cohort vs age class vs fixed boxcar fruit structure
- canopy governor strength
- bounded vs hysteretic THORP correction
- 3-pool vs 4-pool allocation schemes

## Recommended next architecture

Recommended next architecture target:
- Kuijpers common-structure scaffold
- legacy sink-exact fruit law
- De Koning vegetative-demand enhancement
- reduced TOMSIM-style storage seam
- bounded hysteretic THORP root correction
- canopy governor retained
- derived SLA, not SLA-as-driver

Promotion rule:
- do not replace shipped `tomics` until this candidate is calibrated and validated against a tomato greenhouse dataset with fruiting windows longer than the current short example forcing
