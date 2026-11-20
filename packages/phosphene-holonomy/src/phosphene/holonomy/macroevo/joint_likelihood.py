"""Composite taphonomically conditioned diversification likelihood engine.

Integrates mathematical primitives into a joint likelihood evaluator for fossil lineage
diversification under preservation heterogeneity:
- Primitive 1: Exponential diversity-dependent hazard lambda(D)
- Primitive 2: Keiding preservation conditioning P(observable | lifespan)
- Primitive 3: Inhomogeneous Poisson occurrence process
- Primitive 4: Continuous lineage duration and extinction density
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

import numpy as np

from phosphene.holonomy.macroevo.primitives import (
    log_diversity_hazard,
    log_extinction_density,
    log_keiding_conditioning,
    log_poisson_occurrences,
)


@dataclass(frozen=True)
class FossilTaxonRecord:
    """Observed fossil occurrences for a single taxon."""

    taxon_id: str
    lifespan_myr: float
    num_occurrences: int
    mean_standing_diversity: float


def compute_joint_taphonomic_likelihood(
    records: Sequence[FossilTaxonRecord],
    lambda0: float,
    g_l: float,
    mu0: float,
    q_preservation: float,
) -> float:
    """Compute total taphonomically conditioned log-likelihood across fossil records.

    ln L = sum_i [ ln f(Delta t_i | mu) + ln P(k_i | Delta t_i, q) - ln P(observable | Delta t_i, q) + ln lambda(D_i) ]
    """
    total_ll = 0.0

    for rec in records:
        # 1. Extinction duration density
        ll_ext = log_extinction_density(rec.lifespan_myr, mu0)

        # 2. Fossil occurrence Poisson process
        ll_occ = log_poisson_occurrences(rec.num_occurrences, rec.lifespan_myr, q_preservation)

        # 3. Keiding observation conditioning (survival of at least 1 find)
        ll_keiding = log_keiding_conditioning(rec.lifespan_myr, q_preservation)

        # 4. Speciation hazard at time of emergence
        ll_spec = log_diversity_hazard(lambda0, g_l, rec.mean_standing_diversity)

        # Conditional log-likelihood for taxon
        total_ll += ll_ext + ll_occ - ll_keiding + ll_spec

    return float(total_ll)
