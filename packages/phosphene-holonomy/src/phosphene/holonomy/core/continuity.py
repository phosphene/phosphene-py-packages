"""holonomy.core.continuity - Generalized conservation laws and temporal integration."""

from __future__ import annotations

from dataclasses import dataclass
import numpy as np

from phosphene.holonomy.core.manifold import State
from phosphene.holonomy.core.forcing import ForcingField
from phosphene.holonomy.core.transfer import TransferClosure


def compute_flux_divergence(flux: np.ndarray) -> np.ndarray:
    """Compute divergence of vector or tensor flux field J: div(J).

    If flux has the same shape as state (direct rate/growth field), returns flux directly.
    If flux has an extra vector trailing dimension, computes the standard spatial divergence.
    """
    if flux.ndim == 1:
        return np.gradient(flux)

    # If the last dimension is the vector components of a lower-dimensional field:
    # e.g., spatial field (Ny, Nx) with vector components (..., 2)
    spatial_ndim = flux.ndim - 1
    if spatial_ndim >= 1 and flux.shape[-1] == spatial_ndim:
        div = np.zeros(flux.shape[:-1], dtype=np.float64)
        for axis in range(spatial_ndim):
            comp = flux[..., axis]
            grad_axis = np.gradient(comp, axis=axis)
            div += grad_axis
        return div

    # For general point configurations or scalar fields where flux is already dM/dt:
    return flux


def next_state(
    current_state: State,
    forcing: ForcingField,
    closure: TransferClosure,
    dt: float,
    relaxation_rate: float = 0.0,
) -> State:
    """Advance State forward by dt under conservation law: dM/dt = -div(J) - R*M."""
    flux = closure(current_state, forcing)
    div_j = compute_flux_divergence(flux)

    # dM/dt = -div(J) - relaxation
    rate = -div_j - relaxation_rate * current_state.values
    new_values = current_state.values + rate * dt

    return State.create(
        manifold=current_state.manifold,
        values=new_values,
        step_index=current_state.step_index + 1,
        time=current_state.time + dt,
    )
