"""phosphene-holonomy - Generalized mathematical engine for path-dependent morphodynamics."""

from phosphene.holonomy.core import (
    Manifold,
    State,
    ForcingField,
    ControlLoop,
    TransferClosure,
    linear_gradient_transfer,
    compute_flux_divergence,
    next_state,
    EvolutionTrace,
    HolonomyDefect,
    evolution_trace,
)
from phosphene.holonomy import geomorph
from phosphene.holonomy import morphometrics
from phosphene.holonomy import macroevo

__version__ = "0.2.0"

__all__ = [
    # Core Mathematical Kernel
    "Manifold",
    "State",
    "ForcingField",
    "ControlLoop",
    "TransferClosure",
    "linear_gradient_transfer",
    "compute_flux_divergence",
    "next_state",
    "EvolutionTrace",
    "HolonomyDefect",
    "evolution_trace",
    # Domain Dialects
    "geomorph",
    "morphometrics",
    "macroevo",
]
