"""holonomy.morphometrics.remodeling - Structural continuity and morphological defect."""

from __future__ import annotations

import numpy as np

from phosphene.holonomy.core.manifold import State
from phosphene.holonomy.core.forcing import ControlLoop, ForcingField
from phosphene.holonomy.core.transfer import TransferClosure
from phosphene.holonomy.core.trace import EvolutionTrace, HolonomyDefect, evolution_trace
from phosphene.holonomy.morphometrics.configuration import Configuration


def allometric_growth_closure(allometric_coefficients: np.ndarray) -> TransferClosure:
    """Closure modeling differential allometric growth along ontogenetic stress gradients."""
    coeffs = np.array(allometric_coefficients, dtype=np.float64, copy=True)

    def closure(state: State, forcing: ForcingField) -> np.ndarray:
        # Strain / loading drives proportional growth
        growth = coeffs * state.values
        if forcing.values.shape == state.values.shape:
            growth *= (1.0 + forcing.values)
        return growth

    return closure


def ontogenetic_trace(
    initial_config: Configuration,
    loading_cycle: ControlLoop,
    growth_closure: TransferClosure,
) -> EvolutionTrace:
    """Evaluate full ontogenetic evolution trace of cranial landmark configurations."""
    return evolution_trace(initial_config.state, loading_cycle, growth_closure)


def morphological_defect(trace: EvolutionTrace) -> HolonomyDefect:
    """Calculate the morphological defect: permanent skeletal divergence across cycles."""
    return trace.defect()
