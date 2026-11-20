"""holonomy.core.forcing - Parameterized control loops and external driving fields."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence, Iterator
import numpy as np


@dataclass(frozen=True)
class ForcingField:
    """Immutable external driving field evaluated at a specific point in time."""

    time: float
    values: np.ndarray

    def __post_init__(self) -> None:
        self.values.flags.writeable = False

    @classmethod
    def create(cls, time: float, values: np.ndarray) -> ForcingField:
        vals = np.array(values, dtype=np.float64, copy=True)
        return cls(time=time, values=vals)


@dataclass(frozen=True)
class ControlLoop:
    """Ordered schedule of forcing conditions traversing a closed cycle in parameter space.

    Guarantees F(0) == F(T) over period T.
    """

    period: float
    steps: Sequence[ForcingField]

    def __post_init__(self) -> None:
        if len(self.steps) < 2:
            raise ValueError("ControlLoop must contain at least 2 steps")

    def __len__(self) -> int:
        return len(self.steps)

    def __iter__(self) -> Iterator[ForcingField]:
        return iter(self.steps)

    @classmethod
    def sinusoidal(cls, period: float, num_steps: int, shape: tuple[int, ...], amplitude: float = 1.0) -> ControlLoop:
        """Construct canonical sinusoidal control loop with period T."""
        times = np.linspace(0.0, period, num_steps, endpoint=False)
        dt = period / num_steps
        steps: list[ForcingField] = []
        for t in times:
            val = amplitude * np.sin(2.0 * np.pi * t / period)
            field = np.full(shape, val, dtype=np.float64)
            steps.append(ForcingField.create(time=float(t), values=field))
        # Append closure step at t=period matching t=0
        closure_field = np.full(shape, 0.0, dtype=np.float64)
        steps.append(ForcingField.create(time=float(period), values=closure_field))
        return cls(period=period, steps=tuple(steps))
