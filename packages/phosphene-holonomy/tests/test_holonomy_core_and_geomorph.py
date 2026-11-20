"""Unit and property tests for the generalized core engine and geomorph dialect."""

import numpy as np
import pytest

from phosphene.holonomy.core import (
    Manifold,
    State,
    ControlLoop,
    ForcingField,
    EvolutionTrace,
    HolonomyDefect,
    evolution_trace,
    linear_gradient_transfer,
    compute_flux_divergence,
)
from phosphene.holonomy.geomorph import (
    Bed,
    Flow,
    sinusoidal_hydrograph,
    meyer_peter_muller,
    next_bed,
    bed_evolution_trace,
    holonomy_defect,
)


@pytest.fixture
def spatial_grid() -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    x = np.linspace(0, 1000, 21)
    y = np.linspace(0, 500, 11)
    X, Y = np.meshgrid(x, y)
    elevation = -10.0 + 2.0 * np.sin(2.0 * np.pi * X / 1000.0) - (Y / 100.0)
    return x, y, elevation


def test_core_manifold_immutability(spatial_grid):
    x, y, elevation = spatial_grid
    m = Manifold.from_grid(x, y, elevation)
    assert not m.coordinates[0].flags.writeable
    assert not m.coordinates[1].flags.writeable
    assert not m.reference_state.flags.writeable

    with pytest.raises(ValueError):
        m.reference_state[0, 0] = 999.0


def test_core_evolution_trace_and_defect(spatial_grid):
    x, y, elevation = spatial_grid
    m = Manifold.from_grid(x, y, elevation)
    st0 = State.create(m, elevation, step_index=0, time=0.0)

    loop = ControlLoop.sinusoidal(period=3600.0, num_steps=12, shape=m.shape, amplitude=1.0)
    closure = linear_gradient_transfer(diffusion_coeff=0.05)

    trace = evolution_trace(st0, loop, closure)
    assert len(trace) == 13
    assert trace.initial_state is st0

    defect = trace.defect()
    assert isinstance(defect, HolonomyDefect)
    assert defect.norm >= 0.0
    assert not defect.delta_values.flags.writeable

    # Verify zero-loss historical rollback
    st_mid = trace.rollback(6)
    assert st_mid.step_index == 6


def test_geomorph_bed_and_exner(spatial_grid):
    x, y, elevation = spatial_grid
    bed = Bed.from_elevation(x, y, elevation)
    assert not bed.elevation.flags.writeable
    assert isinstance(bed.total_volume, float)

    gx, gy = bed.slope
    assert gx.shape == bed.elevation.shape
    assert gy.shape == bed.elevation.shape

    # Run cyclic hydrograph
    hydrograph = sinusoidal_hydrograph(period=43200.0, num_steps=12, shape=bed.elevation.shape, peak_shear=1.5)
    closure = meyer_peter_muller(critical_shear=0.047)

    trace = bed_evolution_trace(bed, hydrograph, closure, porosity=0.4)
    assert len(trace) == 13

    defect = holonomy_defect(trace)
    assert defect.norm > 0.0  # Hysteresis confirmed
