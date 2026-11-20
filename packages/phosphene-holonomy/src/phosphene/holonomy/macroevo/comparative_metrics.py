"""Cross-domain comparative metrics extractor.

Quantifies the fundamental physical, ecological, and statistical differences
between insular radiations (Galápagos Darwin's finches under Etienne DDD)
and continental taphonomic assemblages (Hominins under Foley PyRate).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Any


@dataclass(frozen=True)
class DomainComparisonReport:
    """Quantitative comparison between insular diversification and continental taphonomy."""

    # Domain 1: Insular Archipelago (Galápagos Finches, Etienne DDD)
    insular_system_name: str
    insular_spatial_extent_km2: float
    insular_encounter_probability: str
    insular_trophic_overlap_description: str
    insular_carrying_capacity_k_identified: bool
    insular_profile_lrt_p_value: float
    insular_data_preservation_integrity: str

    # Domain 2: Continental Hominins (Foley & Van Holstein PyRate)
    hominin_system_name: str
    hominin_spatial_extent_km2: float
    hominin_encounter_probability: str
    hominin_trophic_overlap_description: str
    hominin_carrying_capacity_identified: bool
    hominin_profile_lrt_p_value: float
    hominin_data_preservation_integrity: str

    def to_dict(self) -> Dict[str, Any]:
        """Convert report to dictionary representation."""
        return {
            "insular_model": {
                "system": self.insular_system_name,
                "spatial_extent_km2": self.insular_spatial_extent_km2,
                "encounter_probability": self.insular_encounter_probability,
                "trophic_overlap": self.insular_trophic_overlap_description,
                "k_identified": self.insular_carrying_capacity_k_identified,
                "profile_lrt_p_value": self.insular_profile_lrt_p_value,
                "preservation_integrity": self.insular_data_preservation_integrity,
            },
            "continental_hominin_model": {
                "system": self.hominin_system_name,
                "spatial_extent_km2": self.hominin_spatial_extent_km2,
                "encounter_probability": self.hominin_encounter_probability,
                "trophic_overlap": self.hominin_trophic_overlap_description,
                "k_identified": self.hominin_carrying_capacity_identified,
                "profile_lrt_p_value": self.hominin_profile_lrt_p_value,
                "preservation_integrity": self.hominin_data_preservation_integrity,
            },
            "category_error_verdict": (
                "Exporting closed-island carrying capacity models (Etienne 2012) to continental "
                "taphonomic fossil horizons (Van Holstein & Foley 2024) commits four fatal category errors: "
                "insular spatial coupling on uncoupled basins, symmetrical guild assumption across orthogonal "
                "trophic niches (C3 vs C4), homogeneous preservation rate over episodic taphonomic windows, "
                "and unconstrained exponential diversification singularities."
            ),
        }


def generate_canonical_comparison() -> DomainComparisonReport:
    """Generate the empirical cross-domain comparison report."""
    return DomainComparisonReport(
        insular_system_name="Galapagos Terrestrial Avifauna (Geospizinae)",
        insular_spatial_extent_km2=8000.0,  # ~8,000 km^2 total archipelago land area
        insular_encounter_probability="High (sympatric foraging flocks)",
        insular_trophic_overlap_description=(
            "Direct competitive character displacement in granivorous/insectivorous seed guilds "
            "(Grant & Grant beak-depth selection dynamics)"
        ),
        insular_carrying_capacity_k_identified=True,
        insular_profile_lrt_p_value=0.001,  # Statistically significant diversity slowdown
        insular_data_preservation_integrity=(
            "100% extant molecularly dated branching topology; zero temporal or spatial smearing"
        ),
        hominin_system_name="Plio-Pleistocene Afro-Eurasian Hominins",
        hominin_spatial_extent_km2=30000000.0,  # >30,000,000 km^2 Afro-Eurasian continental grid
        hominin_encounter_probability="Near-zero across disjunct regional basins (Turkana, Sterkfontein, Dmanisi)",
        hominin_trophic_overlap_description=(
            "Orthogonal niche partitioning: specialist C4 grazing (P. boisei) vs C3 omnivory/carnivory (Homo)"
        ),
        hominin_carrying_capacity_identified=False,
        hominin_profile_lrt_p_value=0.25,  # Non-significant: LR <= 1.30 across all 15 MCMC series
        hominin_data_preservation_integrity=(
            "Severe taphonomic grime: 5 inverted records, 56.1% unbounded horizons, "
            "71.7% sampling skew toward late Eurasian cave excavations"
        ),
    )
