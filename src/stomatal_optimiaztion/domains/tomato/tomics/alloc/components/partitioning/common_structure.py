from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True, slots=True)
class CommonStructureSignals:
    """Reduced Kuijpers common-structure snapshot for diagnostics."""

    xA_assimilate_buffer_g_m2: float
    x_leaf_g_m2: float
    x_stem_root_g_m2: float
    x_fruit_g_m2: float
    p_g_ch2o_m2_step: float
    gr_g_ch2o_m2_step: float
    g_g_dm_m2_step: float
    m_g_ch2o_m2_step: float
    h1_fruit_harvest_g_m2_step: float
    h2_leaf_harvest_g_m2_step: float

    def to_dict(self) -> dict[str, float]:
        return asdict(self)


def build_common_structure_snapshot(
    *,
    assimilate_buffer_g: float,
    leaf_biomass_g: float | None = None,
    stem_root_biomass_g: float | None = None,
    fruit_biomass_g: float | None = None,
    structural_biomass_g: float | None = None,
    photosynthesis_g: float,
    growth_respiration_g: float,
    growth_g: float,
    maintenance_g: float,
    fruit_harvest_g: float,
    leaf_harvest_g: float,
) -> dict[str, float]:
    total_structural = max(float(structural_biomass_g or 0.0), 0.0)
    fruit_mass = max(float(fruit_biomass_g or 0.0), 0.0)
    leaf_mass = max(float(leaf_biomass_g or 0.0), 0.0)
    stem_root_mass = max(float(stem_root_biomass_g or 0.0), 0.0)
    if leaf_mass <= 0.0 and stem_root_mass <= 0.0 and total_structural > 0.0:
        residual = max(total_structural - fruit_mass, 0.0)
        leaf_mass = residual * 0.70
        stem_root_mass = residual * 0.30
    snapshot = CommonStructureSignals(
        xA_assimilate_buffer_g_m2=float(assimilate_buffer_g),
        x_leaf_g_m2=leaf_mass,
        x_stem_root_g_m2=stem_root_mass,
        x_fruit_g_m2=fruit_mass,
        p_g_ch2o_m2_step=float(photosynthesis_g),
        gr_g_ch2o_m2_step=float(growth_respiration_g),
        g_g_dm_m2_step=float(growth_g),
        m_g_ch2o_m2_step=float(maintenance_g),
        h1_fruit_harvest_g_m2_step=float(fruit_harvest_g),
        h2_leaf_harvest_g_m2_step=float(leaf_harvest_g),
    )
    return snapshot.to_dict()
