"""holonomy.core.capacity - Explicit boundary and carrying-capacity edge value objects.

Maps ecological or physical ceiling constraints (S <= K) into pure, immutable
data objects separated from linear algebra and matrix exponentiation.

Genealogy:
    Rung: 1–3 boundary primitive (pure stdlib ``math`` + read-only ``numpy`` vector).
    Core Mapping: Instantiates the ``CapacityEdge`` primitive across all dialects.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Literal
import numpy as np


@dataclass(frozen=True)
class CapacityEdge:
    """Explicit carrying-capacity boundary value object separating S <= K from linear algebra.

    Genealogy:
        Rung: 0/1 boundary descriptor; consumed by Rung 2–3 Metzler generators.
        Literature: MacArthur & Wilson (1967); Etienne et al. (2012) Proc. R. Soc. B 279:1300–1309.

    Objective:
        headroom = K - k
        regime in {"saturated_ceiling" (<= 0), "boundary_grazing" (<= 2), "interior_radiation" (> 2)}

    Dimensions:
        k: [lineages] Current observed standing lineage count (int >= 0).
        K: [lineages] Carrying capacity ceiling (float > 0).
        headroom: [lineages] Remaining niche headroom (K - k).

    Boundary & Falsification Semantics:
        - k < 0, K <= 0, or non-finite K -> raises ValueError.
        - headroom <= 0.0 -> regime == "saturated_ceiling", active_ghost_ceiling == 0.
    """

    k: int
    K: float

    def __post_init__(self) -> None:
        if self.k < 0:
            raise ValueError(f"Observed lineage count k must be >= 0, got {self.k}")
        if not math.isfinite(self.K) or self.K <= 0.0:
            raise ValueError(f"Carrying capacity K must be finite and > 0.0, got {self.K}")

    @property
    def headroom(self) -> float:
        """Remaining ecological/physical capacity headroom (K - k) [lineages]."""
        return self.K - float(self.k)

    @property
    def active_ghost_ceiling(self) -> int:
        """Maximum number of unobserved lineages that can exist below K."""
        if self.headroom <= 0.0:
            return 0
        return int(math.ceil(self.headroom))

    @property
    def regime(self) -> Literal["saturated_ceiling", "boundary_grazing", "interior_radiation"]:
        """Discrete operational regime relative to the carrying-capacity ceiling."""
        if self.headroom <= 0.0:
            return "saturated_ceiling"
        if self.headroom <= 2.0:
            return "boundary_grazing"
        return "interior_radiation"


def capacity_throttle(
    edge: CapacityEdge,
    n_max: int,
    lam0: float,
    mu0: float = 0.0,
    dd_model: float = 1.3,
) -> np.ndarray:
    """Per-state capacity-throttled speciation rate vector for unobserved states j = 0..n_max.

    Genealogy:
        Rung: 1 (Read-only 1D ``numpy`` vector).
        Collapses To: Constant scalar ``lam0`` for all j as K -> inf.
        Literature: Etienne et al. (2012) DDD models 1.3 (linear to K) and 1.0 (linear to lam0 - mu0).

    Objective:
        dd_model == 1.3: lam(k + j) = max(0, lam0 * (1 - (k + j) / K))
        dd_model == 1.0: lam(k + j) = max(0, lam0 - (lam0 - mu0) * (k + j) / K)

    Dimensions:
        edge: CapacityEdge with k, K [lineages].
        n_max: [lineages] Maximum unobserved lineage index (int >= 0).
        lam0, mu0: [T^-1] Baseline speciation and extinction rates (>= 0).
        Returns: Read-only 1D float64 array of shape (n_max + 1,) [T^-1].

    Boundary & Falsification Semantics:
        - n_max < 0, lam0 < 0, mu0 < 0, or non-finite rates -> raises ValueError.
        - When edge.headroom <= 0.0 under dd_model == 1.3, returns all-zero vector.

    Invariants & Oracles:
        - Output array enforces ``flags.writeable == False``.
        - Entrywise non-negative and non-increasing in j when lam0 >= mu0.
    """
    if n_max < 0:
        raise ValueError(f"n_max must be >= 0, got {n_max}")
    if not math.isfinite(lam0) or lam0 < 0.0:
        raise ValueError(f"lam0 must be finite and >= 0.0, got {lam0}")
    if not math.isfinite(mu0) or mu0 < 0.0:
        raise ValueError(f"mu0 must be finite and >= 0.0, got {mu0}")

    j = np.arange(n_max + 1, dtype=np.float64)
    if dd_model == 1.3:
        if edge.headroom <= 0.0:
            out = np.zeros(n_max + 1, dtype=np.float64)
        else:
            out = np.maximum(0.0, lam0 * (1.0 - (edge.k + j) / edge.K))
    else:
        out = np.maximum(0.0, lam0 - (lam0 - mu0) * (edge.k + j) / edge.K)
    out.flags.writeable = False
    return out


# Backward-compatibility alias
evaluate_capacity_throttle = capacity_throttle
