"""holonomy.core.capacity - Explicit boundary and carrying capacity edge value objects."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Literal
import numpy as np


@dataclass(frozen=True)
class CapacityEdge:
    """Separates physical/ecological ceiling constraints (S <= K) from linear algebra.

    Exposes headroom (K - k) and discrete regime labels as inspectable data.
    """

    k: int
    K: float

    @property
    def headroom(self) -> float:
        return self.K - float(self.k)

    @property
    def active_ghost_ceiling(self) -> int:
        if self.headroom <= 0.0:
            return 0
        return int(math.ceil(self.headroom))

    @property
    def regime(self) -> Literal["saturated_ceiling", "boundary_grazing", "interior_radiation"]:
        if self.headroom <= 0.0:
            return "saturated_ceiling"
        if self.headroom <= 2.0:
            return "boundary_grazing"
        return "interior_radiation"


def evaluate_capacity_throttle(edge: CapacityEdge, n_max: int, lam0: float) -> np.ndarray:
    """Evaluate per-state capacity throttling vector for unobserved states j = 0..n_max."""
    j = np.arange(n_max + 1, dtype=np.float64)
    if edge.headroom <= 0.0:
        out = np.zeros(n_max + 1, dtype=np.float64)
    else:
        out = np.maximum(0.0, lam0 * (1.0 - (edge.k + j) / edge.K))
    out.flags.writeable = False
    return out
