"""holonomy.geomorph.exner - Exner sediment mass conservation and cyclic bed defect."""

from __future__ import annotations

import numpy as np

from phosphene.holonomy.core.manifold import State
from phosphene.holonomy.core.forcing import ControlLoop, ForcingField
from phosphene.holonomy.core.transfer import TransferClosure
from phosphene.holonomy.core.trace import EvolutionTrace, HolonomyDefect, evolution_trace
from phosphene.holonomy.geomorph.bed import Bed
from phosphene.holonomy.geomorph.flux import flux_divergence


def next_bed(
    current_bed: Bed,
    flow_forcing: ForcingField,
    transport_closure: TransferClosure,
    dt: float,
    porosity: float = 0.4,
) -> Bed:
    """Advance bed elevation forward by dt via Exner conservation:

    d_eta/dt = -1 / (1 - porosity) * div(q_s)
    """
    flux = transport_closure(current_bed.state, flow_forcing)
    div_qs = flux_divergence(flux)
    d_eta = (-1.0 / (1.0 - porosity)) * div_qs * dt
    new_elevation = current_bed.elevation + d_eta

    new_state = State.create(
        manifold=current_bed.state.manifold,
        values=new_elevation,
        step_index=current_bed.state.step_index + 1,
        time=current_bed.state.time + dt,
    )
    return Bed(state=new_state)


def bed_evolution_trace(
    initial_bed: Bed,
    hydrograph_loop: ControlLoop,
    transport_closure: TransferClosure,
    porosity: float = 0.4,
) -> EvolutionTrace:
    """Evaluate full evolution trace of bed states across a cyclic hydrograph."""
    # Scale transfer closure by porosity factor for Exner compatibility
    def exner_transfer(state: State, forcing: ForcingField) -> np.ndarray:
        raw_flux = transport_closure(state, forcing)
        return raw_flux / (1.0 - porosity)

    return evolution_trace(initial_bed.state, hydrograph_loop, exner_transfer)


def holonomy_defect(trace: EvolutionTrace) -> HolonomyDefect:
    """Calculate the closed-loop morphological bed defect delta_eta."""
    return trace.defect()
