"""holonomy.geomorph.flux - Solid sediment discharge closures and flux divergence."""

from __future__ import annotations

import numpy as np

from phosphene.holonomy.core.manifold import State
from phosphene.holonomy.core.forcing import ForcingField
from phosphene.holonomy.core.continuity import compute_flux_divergence


def meyer_peter_muller(
    critical_shear: float = 0.047,
    transport_coeff: float = 8.0,
) -> callable:
    """Canonical Meyer-Peter & Müller (1948) bedload transport closure:

    q_s = transport_coeff * max(0, tau - tau_c)^1.5 * (-grad(eta) / |grad(eta)|)
    """
    def closure(state: State, forcing: ForcingField) -> np.ndarray:
        gy, gx = np.gradient(state.values)
        grad_norm = np.sqrt(gx**2 + gy**2) + 1e-12
        # Unit direction down-slope
        dir_x = -gx / grad_norm
        dir_y = -gy / grad_norm

        excess_shear = np.maximum(0.0, np.abs(forcing.values) - critical_shear)
        magnitude = transport_coeff * (excess_shear**1.5)

        qx = magnitude * dir_x
        qy = magnitude * dir_y
        return np.stack([qy, qx], axis=-1)

    return closure


def flux_divergence(solid_flux: np.ndarray) -> np.ndarray:
    """Compute divergence of solid sediment discharge: div(q_s)."""
    return compute_flux_divergence(solid_flux)
