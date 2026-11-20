"""holonomy.core.transfer - Constitutive transfer operators and flux closures."""

from __future__ import annotations

from typing import Callable
import numpy as np

from phosphene.holonomy.core.manifold import State
from phosphene.holonomy.core.forcing import ForcingField

# Generic transfer closure: (State, ForcingField) -> generalized flux field
TransferClosure = Callable[[State, ForcingField], np.ndarray]


def linear_gradient_transfer(diffusion_coeff: float = 1.0) -> TransferClosure:
    """Canonical linear diffusive transfer operator: J = -D * grad(State)."""
    def closure(state: State, forcing: ForcingField) -> np.ndarray:
        # Simple finite-difference gradient
        grad = np.gradient(state.values)
        flux = -diffusion_coeff * np.stack(grad, axis=-1)
        # Scale by forcing field intensity
        if forcing.values.shape == state.values.shape:
            flux *= np.expand_dims(forcing.values, axis=-1)
        return flux

    return closure
