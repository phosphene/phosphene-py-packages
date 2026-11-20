"""holonomy.morphometrics.configuration - Skeletal landmark configurations in Kendall shape space."""

from __future__ import annotations

from dataclasses import dataclass
import numpy as np

from phosphene.holonomy.core.manifold import Manifold, State


@dataclass(frozen=True)
class Configuration:
    """Immutable 3D morphological landmark configuration (k landmarks x m dimensions)."""

    state: State

    @classmethod
    def from_landmarks(cls, landmarks: np.ndarray, time: float = 0.0) -> Configuration:
        coords = np.array(landmarks, dtype=np.float64, copy=True)
        # Coordinate indices along landmark axes
        c_axes = tuple(np.arange(s, dtype=np.float64) for s in coords.shape)
        m = Manifold(coordinates=c_axes, reference_state=coords)
        st = State.create(m, coords, step_index=0, time=time)
        return cls(state=st)

    @property
    def landmarks(self) -> np.ndarray:
        return self.state.values

    @property
    def centroid_size(self) -> float:
        """Centroid size: Frobenius norm of mean-centered landmark configuration."""
        centered = self.landmarks - np.mean(self.landmarks, axis=0, keepdims=True)
        return float(np.linalg.norm(centered))
