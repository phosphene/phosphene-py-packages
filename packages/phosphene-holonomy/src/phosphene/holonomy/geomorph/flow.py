"""holonomy.geomorph.flow - Hydrodynamic fluid forcing fields."""

from __future__ import annotations

from dataclasses import dataclass
import numpy as np

from phosphene.holonomy.core.forcing import ControlLoop, ForcingField


@dataclass(frozen=True)
class Flow:
    """Immutable hydrodynamic forcing field (depth, velocity, boundary shear stress)."""

    field: ForcingField

    @classmethod
    def from_shear_stress(cls, time: float, shear_stress: np.ndarray) -> Flow:
        f = ForcingField.create(time=time, values=shear_stress)
        return cls(field=f)

    @property
    def shear_stress(self) -> np.ndarray:
        return self.field.values

    @property
    def time(self) -> float:
        return self.field.time


def sinusoidal_hydrograph(period: float, num_steps: int, shape: tuple[int, ...], peak_shear: float = 1.5) -> ControlLoop:
    """Generate cyclic spring-neap or tidal hydrograph loop."""
    return ControlLoop.sinusoidal(period=period, num_steps=num_steps, shape=shape, amplitude=peak_shear)
