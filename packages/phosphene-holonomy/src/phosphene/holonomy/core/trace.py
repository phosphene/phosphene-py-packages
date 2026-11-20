"""holonomy.core.trace - Immutable evolution traces and holonomy defect audits."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence, Iterator, Tuple
import numpy as np

from phosphene.holonomy.core.manifold import State
from phosphene.holonomy.core.forcing import ControlLoop, ForcingField
from phosphene.holonomy.core.transfer import TransferClosure
from phosphene.holonomy.core.continuity import next_state


@dataclass(frozen=True)
class HolonomyDefect:
    """Closed-loop path-dependent residue: delta_M = M(T) - M(0)."""

    initial_state: State
    final_state: State
    duration: float

    @property
    def delta_values(self) -> np.ndarray:
        delta = self.final_state.values - self.initial_state.values
        delta.flags.writeable = False
        return delta

    @property
    def norm(self) -> float:
        """L2 Euclidean Frobenius norm of net permanent displacement."""
        return float(np.linalg.norm(self.delta_values))

    @property
    def max_absolute_defect(self) -> float:
        return float(np.max(np.abs(self.delta_values)))


@dataclass(frozen=True)
class EvolutionTrace:
    """Ordered, append-only lineage of immutable states along a control trajectory."""

    states: Tuple[State, ...]

    def __post_init__(self) -> None:
        if len(self.states) == 0:
            raise ValueError("EvolutionTrace must contain at least one state")

    def __len__(self) -> int:
        return len(self.states)

    def __iter__(self) -> Iterator[State]:
        return iter(self.states)

    def __getitem__(self, index: int) -> State:
        return self.states[index]

    @property
    def initial_state(self) -> State:
        return self.states[0]

    @property
    def final_state(self) -> State:
        return self.states[-1]

    def rollback(self, target_step: int) -> State:
        """Retrieve historical state snapshot without data loss."""
        for st in self.states:
            if st.step_index == target_step:
                return st
        raise IndexError(f"Step {target_step} not found in EvolutionTrace")

    def defect(self) -> HolonomyDefect:
        """Calculate closed-loop holonomy defect across full trace duration."""
        duration = self.final_state.time - self.initial_state.time
        return HolonomyDefect(
            initial_state=self.initial_state,
            final_state=self.final_state,
            duration=duration,
        )


def evolution_trace(
    initial_state: State,
    loop: ControlLoop,
    closure: TransferClosure,
) -> EvolutionTrace:
    """Pure transformation integrating State forward through a ControlLoop."""
    recorded_states: list[State] = [initial_state]
    current = initial_state
    steps = loop.steps

    for i in range(len(steps) - 1):
        f_current = steps[i]
        f_next = steps[i + 1]
        dt = f_next.time - f_current.time
        current = next_state(current, f_current, closure, dt)
        recorded_states.append(current)

    return EvolutionTrace(states=tuple(recorded_states))
