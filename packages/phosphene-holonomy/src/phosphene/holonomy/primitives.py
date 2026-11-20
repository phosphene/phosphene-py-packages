"""holonomy.primitives - Core mathematical primitives and data-preserving architecture.

Mapping morphodynamic math to immutable, pure-functional package primitives:
- holonomy.Manifold: Immutable reference bathymetry and spatial discretization (M_0).
- holonomy.Connection: Sediment-flux differential operator -div(q_s).
- holonomy.Loop: Parameterized trajectory of hydrodynamic boundary conditions.
- holonomy.Defect: Net morphological displacement delta_eta = oint partial_t eta dt.
- SurfaceState: Immutable state pairing elevation with zero-copy reference to Manifold.
- holonomy.Trace: Explicit lineage graph of immutable snapshots along a Loop.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Iterator, Optional, Sequence, Tuple
import numpy as np


@dataclass(frozen=True)
class Manifold:
    """holonomy.Manifold: Immutable reference bathymetry and spatial discretization.

    Represents the initial coordinate surface M_0 held strictly read-only so
    baseline grids survive every simulation and evaluation run intact without
    accidental in-place mutation.
    """

    x_coords: np.ndarray  # (Nx,) 1D or (Ny, Nx) 2D
    y_coords: np.ndarray  # (Ny,) 1D or (Ny, Nx) 2D
    bathymetry_0: np.ndarray  # (Ny, Nx) initial reference elevation/depth eta_0
    dx: float
    dy: float

    def __post_init__(self) -> None:
        # Enforce read-only memory flags on underlying numpy arrays
        self.x_coords.flags.writeable = False
        self.y_coords.flags.writeable = False
        self.bathymetry_0.flags.writeable = False

        if self.dx <= 0.0 or self.dy <= 0.0:
            raise ValueError(f"Spatial steps dx and dy must be strictly positive, got dx={self.dx}, dy={self.dy}")

        if self.bathymetry_0.ndim != 2:
            raise ValueError(f"bathymetry_0 must be 2D array (Ny, Nx), got ndim={self.bathymetry_0.ndim}")

    @property
    def shape(self) -> Tuple[int, int]:
        return self.bathymetry_0.shape

    @classmethod
    def from_grid(
        cls,
        x: np.ndarray,
        y: np.ndarray,
        elevation: np.ndarray,
    ) -> Manifold:
        """Construct an immutable Manifold from 1D coordinates and 2D elevation grid."""
        dx = float(np.diff(x)[0]) if len(x) > 1 else 1.0
        dy = float(np.diff(y)[0]) if len(y) > 1 else 1.0
        return cls(
            x_coords=np.array(x, copy=True),
            y_coords=np.array(y, copy=True),
            bathymetry_0=np.array(elevation, copy=True),
            dx=dx,
            dy=dy,
        )

    def initial_state(self) -> SurfaceState:
        """Create the initial SurfaceState at t=0 tied to this manifold."""
        return SurfaceState(
            manifold=self,
            elevation=np.array(self.bathymetry_0, copy=True),
            time=0.0,
            step_index=0,
        )


@dataclass(frozen=True)
class SurfaceState:
    """Immutable state container for bed surface elevation.

    Pairs a newly allocated elevation field eta with a zero-copy reference to the
    static horizontal coordinate manifold M_0, eliminating in-place buffer overwrites
    while avoiding redundant coordinate grid duplication.
    """

    manifold: Manifold
    elevation: np.ndarray  # (Ny, Nx) current elevation eta(x, y, t)
    time: float
    step_index: int

    def __post_init__(self) -> None:
        self.elevation.flags.writeable = False
        if self.elevation.shape != self.manifold.shape:
            raise ValueError(
                f"Elevation shape {self.elevation.shape} does not match Manifold shape {self.manifold.shape}"
            )

    @property
    def displacement(self) -> np.ndarray:
        """Difference between current elevation and reference bathymetry M_0."""
        return self.elevation - self.manifold.bathymetry_0

    @property
    def total_volume(self) -> float:
        """Integrate total sediment volume relative to horizontal zero."""
        return float(np.sum(self.elevation) * self.manifold.dx * self.manifold.dy)


@dataclass(frozen=True)
class HydrodynamicBoundaryCondition:
    """Boundary shear stress, flow velocity, or tidal stage forcing at a given point in time."""

    time: float
    shear_stress_x: np.ndarray  # tau_x (Ny, Nx) or scalar broadcast
    shear_stress_y: np.ndarray  # tau_y (Ny, Nx) or scalar broadcast
    water_depth: Optional[np.ndarray] = None
    label: str = ""


@dataclass(frozen=True)
class Connection:
    """holonomy.Connection: Sediment-flux differential operator -div(q_s).

    The transport rule dictating how boundary shear stress shifts mass between
    neighboring cells without mutating shared arrays.
    
    Given a SurfaceState and a HydrodynamicBoundaryCondition, computes the
    sediment flux q_s and returns the divergence rate:
        partial_t eta = - (1 / (1 - porosity)) * div(q_s)
    """

    porosity: float = 0.4
    transport_law: Optional[Callable[[SurfaceState, HydrodynamicBoundaryCondition], Tuple[np.ndarray, np.ndarray]]] = None

    def __post_init__(self) -> None:
        if not (0.0 <= self.porosity < 1.0):
            raise ValueError(f"Porosity must be in [0, 1), got {self.porosity}")

    def compute_flux(
        self,
        state: SurfaceState,
        forcing: HydrodynamicBoundaryCondition,
    ) -> Tuple[np.ndarray, np.ndarray]:
        """Compute sediment transport flux vector field q_s = (q_sx, q_sy)."""
        if self.transport_law is not None:
            return self.transport_law(state, forcing)

        # Default canonical Grass-type power law transport: q_s = A * |tau|^(3/2) * (tau / |tau|)
        tau_x = np.asarray(forcing.shear_stress_x, dtype=np.float64)
        tau_y = np.asarray(forcing.shear_stress_y, dtype=np.float64)

        if tau_x.shape != state.manifold.shape:
            tau_x = np.broadcast_to(tau_x, state.manifold.shape)
        if tau_y.shape != state.manifold.shape:
            tau_y = np.broadcast_to(tau_y, state.manifold.shape)

        mag_tau = np.sqrt(tau_x**2 + tau_y**2) + 1e-12
        transport_coeff = 0.001
        q_sx = transport_coeff * (mag_tau**1.5) * (tau_x / mag_tau)
        q_sy = transport_coeff * (mag_tau**1.5) * (tau_y / mag_tau)
        return q_sx, q_sy

    def divergence(
        self,
        q_sx: np.ndarray,
        q_sy: np.ndarray,
        dx: float,
        dy: float,
    ) -> np.ndarray:
        """Compute spatial flux divergence div(q_s) = d(q_sx)/dx + d(q_sy)/dy using central differences."""
        grad_qx = np.gradient(q_sx, dx, axis=1)
        grad_qy = np.gradient(q_sy, dy, axis=0)
        return grad_qx + grad_qy

    def transport_rate(
        self,
        state: SurfaceState,
        forcing: HydrodynamicBoundaryCondition,
    ) -> np.ndarray:
        """Compute rate of elevation change partial_t eta = - (1 / (1 - p)) * div(q_s)."""
        q_sx, q_sy = self.compute_flux(state, forcing)
        div_q = self.divergence(q_sx, q_sy, state.manifold.dx, state.manifold.dy)
        rate = -(1.0 / (1.0 - self.porosity)) * div_q
        return rate

    def advance(
        self,
        state: SurfaceState,
        forcing: HydrodynamicBoundaryCondition,
        dt: float,
    ) -> SurfaceState:
        """Advance the Exner equation by dt, returning a newly allocated SurfaceState.

        Ensures immutability: the input state and manifold are never modified.
        """
        if dt <= 0.0:
            raise ValueError(f"Time step dt must be positive, got {dt}")

        rate = self.transport_rate(state, forcing)
        new_elevation = state.elevation + rate * dt

        return SurfaceState(
            manifold=state.manifold,
            elevation=new_elevation,
            time=state.time + dt,
            step_index=state.step_index + 1,
        )


@dataclass(frozen=True)
class Loop:
    """holonomy.Loop: Parameterized trajectory of hydrodynamic boundary conditions.

    An ordered forcing schedule across tidal phases, storm hydrographs, or wave
    climates, parameterized over time or phase angle theta in [0, 2*pi].
    """

    forcings: Sequence[HydrodynamicBoundaryCondition]
    period: float
    name: str = "hydrodynamic_loop"

    def __post_init__(self) -> None:
        if len(self.forcings) == 0:
            raise ValueError("Loop must contain at least one boundary condition forcing")
        if self.period <= 0.0:
            raise ValueError(f"Loop period must be strictly positive, got {self.period}")

    def __len__(self) -> int:
        return len(self.forcings)

    def __iter__(self) -> Iterator[HydrodynamicBoundaryCondition]:
        return iter(self.forcings)

    @classmethod
    def sinusoidal_tide(
        cls,
        manifold: Manifold,
        period: float = 43200.0,  # 12 hours (semi-diurnal tide in seconds)
        num_steps: int = 24,
        peak_shear: float = 1.5,
    ) -> Loop:
        """Construct a closed sinusoidal tidal forcing loop."""
        dt = period / num_steps
        forcings = []
        for i in range(num_steps):
            t = i * dt
            phase = 2.0 * np.pi * (t / period)
            # Tidal current reversing in x direction with minor cross-channel component
            tau_x = peak_shear * np.sin(phase) * np.ones(manifold.shape)
            tau_y = 0.1 * peak_shear * np.cos(phase) * np.ones(manifold.shape)
            forcings.append(
                HydrodynamicBoundaryCondition(
                    time=t,
                    shear_stress_x=tau_x,
                    shear_stress_y=tau_y,
                    label=f"tide_phase_{phase:.2f}",
                )
            )
        return cls(forcings=forcings, period=period, name="sinusoidal_tide")


@dataclass(frozen=True)
class Defect:
    """holonomy.Defect: The net morphological displacement Delta_eta = oint partial_t eta dt.

    The exact geometric residual obtained by comparing preserved initial and final
    states after traversing a forcing cycle or trajectory.
    """

    initial_state: SurfaceState
    final_state: SurfaceState
    duration: float
    delta_eta: np.ndarray = field(init=False)

    def __post_init__(self) -> None:
        if self.initial_state.manifold != self.final_state.manifold:
            raise ValueError("Initial and final states must belong to the identical Manifold M_0")
        diff = self.final_state.elevation - self.initial_state.elevation
        diff.flags.writeable = False
        object.__setattr__(self, "delta_eta", diff)

    @property
    def norm(self) -> float:
        """L2 Frobenius norm of the morphological displacement field."""
        return float(np.linalg.norm(self.delta_eta))

    @property
    def max_displacement(self) -> float:
        """Maximum absolute elevation change over the loop."""
        return float(np.max(np.abs(self.delta_eta)))

    @property
    def net_volume_change(self) -> float:
        """Net volume change across domain (boundary mass flux residual)."""
        dx = self.initial_state.manifold.dx
        dy = self.initial_state.manifold.dy
        return float(np.sum(self.delta_eta) * dx * dy)

    @property
    def has_holonomy(self, tolerance: float = 1e-9) -> bool:
        """Returns True if the closed boundary loop produces non-zero morphological defect."""
        return self.norm > tolerance


@dataclass(frozen=True)
class TraceNode:
    """Single node in an explicit trajectory graph."""

    state: SurfaceState
    forcing_applied: Optional[HydrodynamicBoundaryCondition] = None
    dt: float = 0.0
    parent_index: Optional[int] = None


class Trace:
    """holonomy.Trace: Explicit trajectory graph of immutable state transitions.

    Chaining steps along a Loop records a directed lineage of snapshots,
    enabling instant rollback, mass-conservation audits across arbitrary time
    windows, and clean differentiation through transport closures.
    """

    def __init__(self, initial_state: SurfaceState) -> None:
        self._nodes: list[TraceNode] = [
            TraceNode(state=initial_state, forcing_applied=None, dt=0.0, parent_index=None)
        ]

    def __len__(self) -> int:
        return len(self._nodes)

    def __getitem__(self, index: int) -> SurfaceState:
        return self._nodes[index].state

    @property
    def initial_state(self) -> SurfaceState:
        return self._nodes[0].state

    @property
    def current_state(self) -> SurfaceState:
        return self._nodes[-1].state

    def append(
        self,
        new_state: SurfaceState,
        forcing: HydrodynamicBoundaryCondition,
        dt: float,
    ) -> None:
        """Append an advanced state to the lineage graph."""
        parent_idx = len(self._nodes) - 1
        self._nodes.append(
            TraceNode(
                state=new_state,
                forcing_applied=forcing,
                dt=dt,
                parent_index=parent_idx,
            )
        )

    def traverse(
        self,
        loop: Loop,
        connection: Connection,
        dt: Optional[float] = None,
    ) -> Defect:
        """Traverse a complete Loop using Connection, recording the full Trace lineage and returning the Defect."""
        initial_st = self.current_state
        step_dt = dt if dt is not None else (loop.period / len(loop))

        for forcing in loop:
            next_st = connection.advance(self.current_state, forcing, step_dt)
            self.append(next_st, forcing, step_dt)

        final_st = self.current_state
        return Defect(
            initial_state=initial_st,
            final_state=final_st,
            duration=loop.period,
        )

    def rollback(self, target_step_index: int) -> SurfaceState:
        """Return historical state snapshot without data loss or mutation."""
        for node in self._nodes:
            if node.state.step_index == target_step_index:
                return node.state
        raise IndexError(f"Step index {target_step_index} not found in Trace lineage")

    def mass_conservation_audit(self, start_step: int = 0, end_step: int = -1) -> float:
        """Audit total volume difference between two steps in the trajectory."""
        st_start = self._nodes[start_step].state
        st_end = self._nodes[end_step].state
        return st_end.total_volume - st_start.total_volume
