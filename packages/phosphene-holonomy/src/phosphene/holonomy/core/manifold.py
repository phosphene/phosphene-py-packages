"""holonomy.core.manifold - Generic immutable state manifold and spatial discretization."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence, Tuple
import numpy as np


@dataclass(frozen=True)
class Manifold:
    """Immutable spatial discretization and baseline reference coordinate grid (M_0).

    Guarantees strict immutability of underlying coordinate meshes.
    """

    coordinates: Tuple[np.ndarray, ...]
    reference_state: np.ndarray

    def __post_init__(self) -> None:
        for c in self.coordinates:
            c.flags.writeable = False
        self.reference_state.flags.writeable = False

    @classmethod
    def from_grid(cls, x: np.ndarray, y: np.ndarray, baseline: np.ndarray) -> Manifold:
        """Construct a 2D spatial manifold from 1D coordinate vectors."""
        x_copy = np.array(x, dtype=np.float64, copy=True)
        y_copy = np.array(y, dtype=np.float64, copy=True)
        base_copy = np.array(baseline, dtype=np.float64, copy=True)
        return cls(coordinates=(x_copy, y_copy), reference_state=base_copy)

    @property
    def shape(self) -> Tuple[int, ...]:
        return self.reference_state.shape

    @property
    def ndim(self) -> int:
        return self.reference_state.ndim


@dataclass(frozen=True)
class State:
    """Immutable physical state snapshot residing on a Manifold."""

    manifold: Manifold
    values: np.ndarray
    step_index: int = 0
    time: float = 0.0

    def __post_init__(self) -> None:
        self.values.flags.writeable = False

    @classmethod
    def create(cls, manifold: Manifold, values: np.ndarray, step_index: int = 0, time: float = 0.0) -> State:
        vals = np.array(values, dtype=np.float64, copy=True)
        return cls(manifold=manifold, values=vals, step_index=step_index, time=time)

    @property
    def shape(self) -> Tuple[int, ...]:
        return self.values.shape
