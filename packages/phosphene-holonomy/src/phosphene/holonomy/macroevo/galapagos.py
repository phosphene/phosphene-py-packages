"""Galapagos insular avifauna schema and data loader.

Formalizes the canonical Valente, Phillimore, & Etienne (2015, Ecology Letters)
empirical dataset for island biogeography and diversity-dependent diversification (DAISIE/DDD).
"""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Sequence


class ColonistStatus(str, Enum):
    """Status of island colonist lineage per Valente et al. (2015)."""

    ENDEMIC = "Endemic"
    NON_ENDEMIC = "Non_endemic"
    NON_ENDEMIC_MAX_AGE = "Non_endemic_MaxAge"
    ENDEMIC_MAX_AGE = "Endemic_MaxAge"
    ENDEMIC_AND_NON_ENDEMIC = "Endemic&Non_Endemic"


@dataclass(frozen=True)
class GalapagosClade:
    """Represents an independent colonization event on the Galápagos archipelago."""

    clade_name: str
    status: ColonistStatus
    missing_species: int
    branching_times: tuple[float, ...]  # Branching times in Ma (sorted descending)

    @property
    def is_endemic_radiation(self) -> bool:
        """True if the clade underwent in situ cladogenesis on the island."""
        return self.status == ColonistStatus.ENDEMIC and len(self.branching_times) > 1

    @property
    def species_count(self) -> int:
        """Total known extant/sampled species count for this colonist clade."""
        if len(self.branching_times) > 1:
            return len(self.branching_times) + self.missing_species
        return 1 + self.missing_species

    @property
    def colonization_time(self) -> float:
        """Estimated colonization time (stem age) in Ma."""
        return self.branching_times[0] if self.branching_times else 0.0


@dataclass(frozen=True)
class GalapagosDataset:
    """Container for the complete Galápagos avifaunal radiation dataset."""

    island_age_myr: float
    mainland_pool_size: int
    clades: tuple[GalapagosClade, ...]

    def get_clade(self, name: str) -> GalapagosClade:
        """Retrieve a specific clade by name."""
        for clade in self.clades:
            if clade.clade_name.lower() == name.lower():
                return clade
        raise KeyError(f"Clade '{name}' not found in Galápagos dataset")

    @property
    def finches(self) -> GalapagosClade:
        """Darwin's finches (Geospizinae) radiation."""
        return self.get_clade("Finches")

    @property
    def total_colonizations(self) -> int:
        """Number of independent colonization lineages."""
        return len(self.clades)

    @property
    def total_endemic_species(self) -> int:
        """Total endemic species count across all clades."""
        return sum(c.species_count for c in self.clades if "Endemic" in c.status.value)


def load_galapagos_csv(path: Path) -> GalapagosDataset:
    """Load canonical Galápagos avifauna from CSV datatable."""
    clades: list[GalapagosClade] = []
    with open(path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            raw_brts = [float(x.strip()) for x in row["Branching_times"].split(",") if x.strip()]
            sorted_brts = tuple(sorted(raw_brts, reverse=True))
            clades.append(
                GalapagosClade(
                    clade_name=row["Clade_name"].strip(),
                    status=ColonistStatus(row["Status"].strip()),
                    missing_species=int(row["Missing_species"]),
                    branching_times=sorted_brts,
                )
            )

    return GalapagosDataset(
        island_age_myr=4.0,
        mainland_pool_size=1000,
        clades=tuple(clades),
    )


def load_galapagos_json(path: Path) -> GalapagosDataset:
    """Load canonical Galápagos avifauna from JSON manifest."""
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    clades = [
        GalapagosClade(
            clade_name=item["clade_name"],
            status=ColonistStatus(item["status"]),
            missing_species=item["missing_species"],
            branching_times=tuple(sorted(item["branching_times"], reverse=True)),
        )
        for item in data["clades"]
    ]

    return GalapagosDataset(
        island_age_myr=float(data["island_age_myr"]),
        mainland_pool_size=int(data["mainland_pool_size"]),
        clades=tuple(clades),
    )
