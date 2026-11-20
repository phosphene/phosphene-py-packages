"""holonomy.geomorph.bed - Evolving bathymetric boundary geometry."""

from __future__ import annotations

from dataclasses import dataclass
import numpy as np

from phosphene.holonomy.core.manifold import Manifold, State


@dataclass(frozen=True)
class Bed:
    """Immutable bathymetric bed configuration inhabiting an elevation manifold."""

    state: State

    @classmethod
    def from_elevation(cls, x: np.ndarray, y: np.ndarray, elevation: np.ndarray, time: float = 0.0) -> Bed:
        m = Manifold.from_grid(x, y, elevation)
        st = State.create(m, elevation, step_index=0, time=time)
        return cls(state=st)

    @property
    def elevation(self) -> np.ndarray:
        return self.state.values

    @property
    def slope(self) -> tuple[np.ndarray, np.ndarray]:
        """Spatial gradient of bed elevation (d_eta/dx, d_eta/dy)."""
        gy, gx = np.gradient(self.elevation)
        return gx, gy

    @property
    def total_volume(self) -> float:
        return float(np.sum(self.elevation))
