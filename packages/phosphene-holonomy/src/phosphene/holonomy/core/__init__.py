"""holonomy.core - Generalized mathematical engine for path-dependent dynamical systems."""

from phosphene.holonomy.core.manifold import Manifold, State
from phosphene.holonomy.core.forcing import ControlLoop, ForcingField
from phosphene.holonomy.core.capacity import CapacityEdge, evaluate_capacity_throttle
from phosphene.holonomy.core.transfer import TransferClosure, linear_gradient_transfer
from phosphene.holonomy.core.continuity import compute_flux_divergence, next_state
from phosphene.holonomy.core.trace import EvolutionTrace, HolonomyDefect, evolution_trace

__all__ = [
    "Manifold",
    "State",
    "ForcingField",
    "ControlLoop",
    "CapacityEdge",
    "evaluate_capacity_throttle",
    "TransferClosure",
    "linear_gradient_transfer",
    "compute_flux_divergence",
    "next_state",
    "EvolutionTrace",
    "HolonomyDefect",
    "evolution_trace",
]
