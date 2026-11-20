"""Unit tests for phosphene.holonomy primitives and execution architecture."""

import numpy as np
import pytest

from phosphene.holonomy.primitives import (
    Connection,
    Defect,
    HydrodynamicBoundaryCondition,
    Loop,
    Manifold,
    SurfaceState,
    Trace,
)


@pytest.fixture
def test_manifold() -> Manifold:
    x = np.linspace(0, 1000, 21)
    y = np.linspace(0, 500, 11)
    # Simple synthetic bathymetry with channel trench in the middle
    X, Y = np.meshgrid(x, y)
    elevation = -10.0 + 2.0 * np.sin(2.0 * np.pi * X / 1000.0) - (Y / 100.0)
    return Manifold.from_grid(x, y, elevation)


def test_manifold_immutability(test_manifold: Manifold) -> None:
    """holonomy.Manifold arrays must be read-only."""
    assert not test_manifold.x_coords.flags.writeable
    assert not test_manifold.y_coords.flags.writeable
    assert not test_manifold.bathymetry_0.flags.writeable

    with pytest.raises(ValueError, match="read-only"):
        test_manifold.bathymetry_0[0, 0] = 999.0


def test_surface_state_zero_copy_and_immutability(test_manifold: Manifold) -> None:
    """SurfaceState elevation must be immutable and reference static Manifold."""
    state = test_manifold.initial_state()
    assert state.manifold is test_manifold
    assert not state.elevation.flags.writeable

    with pytest.raises(ValueError, match="read-only"):
        state.elevation[0, 0] = 50.0

    np.testing.assert_allclose(state.elevation, test_manifold.bathymetry_0)
    np.testing.assert_allclose(state.displacement, np.zeros_like(test_manifold.bathymetry_0))


def test_connection_advance_pure_functional(test_manifold: Manifold) -> None:
    """Connection.advance must return a new SurfaceState without mutating prior state."""
    state0 = test_manifold.initial_state()
    conn = Connection(porosity=0.35)

    forcing = HydrodynamicBoundaryCondition(
        time=0.0,
        shear_stress_x=1.5 * np.ones(test_manifold.shape),
        shear_stress_y=np.zeros(test_manifold.shape),
    )

    state1 = conn.advance(state0, forcing, dt=3600.0)

    # Initial state must remain unchanged
    assert state0.time == 0.0
    assert state0.step_index == 0
    assert state1.time == 3600.0
    assert state1.step_index == 1
    assert state0.manifold is state1.manifold
    assert state0 is not state1
    assert state0.elevation is not state1.elevation


def test_loop_and_defect_holonomy(test_manifold: Manifold) -> None:
    """Traversing a Loop through Connection computes non-trivial morphological Defect."""
    loop = Loop.sinusoidal_tide(test_manifold, period=43200.0, num_steps=12, peak_shear=2.0)
    assert len(loop) == 12

    conn = Connection(porosity=0.4)
    state0 = test_manifold.initial_state()
    trace = Trace(state0)

    defect = trace.traverse(loop, conn)

    assert defect.duration == 43200.0
    assert defect.initial_state is state0
    assert defect.final_state is trace.current_state
    assert defect.delta_eta.shape == test_manifold.shape
    assert not defect.delta_eta.flags.writeable
    assert len(trace) == 13  # Initial + 12 steps


def test_trace_lineage_and_rollback(test_manifold: Manifold) -> None:
    """holonomy.Trace allows instant zero-loss rollback to any prior step."""
    loop = Loop.sinusoidal_tide(test_manifold, period=43200.0, num_steps=6, peak_shear=1.0)
    conn = Connection()
    trace = Trace(test_manifold.initial_state())

    trace.traverse(loop, conn)

    # Rollback to step 3
    st3 = trace.rollback(3)
    assert st3.step_index == 3
    assert st3.time == (43200.0 / 6) * 3

    # Mass conservation audit
    vol_diff = trace.mass_conservation_audit(0, -1)
    assert isinstance(vol_diff, float)
