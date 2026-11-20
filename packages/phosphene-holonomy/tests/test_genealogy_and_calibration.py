"""Hypothesis property and oracle calibration suite across the numerical genealogy rungs.

Tests:
1. Rung 2 pure-death collapses to Rung 0 scalar math to machine precision.
2. Rung 3 capacity-bounded solver collapses to Rung 0 Nee-May-Harvey as K -> inf.
3. Rung 2 Padé and Krylov propagators calibrated against Jensen's Uniformization oracle.
4. Vertex-seam continuity across carrying capacity ceiling K = k +/- eps.
5. Chapman-Kolmogorov interval splitting across continuous flow vertices.
6. Stateful HolonomyVertexMachine exercising arbitrary vertex traversals and rollbacks.
"""

from __future__ import annotations

import math
from typing import Callable, Tuple
import numpy as np
import pytest
from hypothesis import given, settings, target, event, strategies as st, HealthCheck
from hypothesis.stateful import RuleBasedStateMachine, rule, invariant, initialize

from phosphene.holonomy.core.capacity import CapacityEdge, evaluate_capacity_throttle
from phosphene.holonomy.macroevo.escalation import (
    BranchingState,
    BranchingTrace,
    rung0_pure_death_logprob,
    rung0_constant_rate_loglik,
    assemble_metzler_generator,
    propagate_uniformized,
    propagate_dense_pade,
    propagate_sparse_krylov,
    step_interval_vertex,
    step_observation_vertex,
    evaluate_with_escalation_ladder,
)


@pytest.fixture(scope="session", params=["dense_pade", "sparse_krylov"])
def fast_propagator(request) -> Callable[[np.ndarray, np.ndarray, float], np.ndarray]:
    if request.param == "dense_pade":
        return propagate_dense_pade
    return propagate_sparse_krylov


@st.composite
def descending_branching_times(draw, min_splits: int = 2, max_splits: int = 5) -> Tuple[float, ...]:
    n_splits = draw(st.integers(min_value=min_splits, max_value=max_splits))
    deltas = draw(
        st.lists(
            st.floats(
                min_value=0.05,
                max_value=2.0,
                allow_nan=False,
                allow_infinity=False,
                allow_subnormal=False,
            ),
            min_size=n_splits,
            max_size=n_splits,
        )
    )
    return tuple(np.cumsum(deltas)[::-1].tolist())


# ============================================================================
# Calibration Tests: Rung-to-Rung Oracles & Vertex-Seam Continuity
# ============================================================================

@settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(
    k=st.integers(min_value=1, max_value=12),
    mu0=st.floats(min_value=0.05, max_value=5.0, allow_nan=False, allow_infinity=False, allow_subnormal=False),
    dt=st.floats(min_value=0.05, max_value=2.0, allow_nan=False, allow_infinity=False, allow_subnormal=False),
)
def test_genealogy_rung2_collapses_to_rung0_pure_death(
    fast_propagator, k: int, mu0: float, dt: float
):
    """When lam0 = 0, Rung 2 matrix semigroup equals Rung 0 scalar exp(-k * mu0 * dt)."""
    edge = CapacityEdge(k=k, K=float(k) + 4.0)
    n_max = edge.active_ghost_ceiling + 2
    p0 = np.zeros(n_max + 1, dtype=np.float64)
    p0[0] = 1.0
    st0 = BranchingState(t=dt, k=k, P=p0)

    st1 = step_interval_vertex(st0, dt=dt, lam0=0.0, mu0=mu0, K=edge.K, propagator=fast_propagator)
    log_p0_r2 = math.log(float(st1.P[0]))
    log_p0_r0 = rung0_pure_death_logprob(dt=dt, k=k, mu0=mu0)

    defect = abs(log_p0_r2 - log_p0_r0)
    target(defect, label="rung2_to_rung0_pure_death_defect")
    assert defect <= 1e-13


@settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(
    branching_times=descending_branching_times(min_splits=2, max_splits=4),
    lam0=st.floats(min_value=0.3, max_value=2.0, allow_nan=False, allow_infinity=False, allow_subnormal=False),
    mu0=st.floats(min_value=0.05, max_value=1.5, allow_nan=False, allow_infinity=False, allow_subnormal=False),
)
def test_genealogy_rung3_collapses_to_rung0_at_large_capacity(
    fast_propagator, branching_times: Tuple[float, ...], lam0: float, mu0: float
):
    """As K -> inf, Rung 3 path likelihood collapses onto Rung 0 scalar closed form."""
    report = evaluate_with_escalation_ladder(
        branching_times=branching_times,
        lam0=lam0,
        mu0=mu0,
        K=1e9,
        propagator=fast_propagator,
    )
    defect = abs(report.escalation_gain)
    target(defect, label="rung3_to_rung0_asymptotic_defect")
    assert defect <= 1e-6


@settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(
    k=st.integers(min_value=2, max_value=8),
    headroom=st.floats(min_value=0.25, max_value=8.0, allow_nan=False, allow_infinity=False, allow_subnormal=False),
    lam0=st.floats(min_value=0.5, max_value=10.0, allow_nan=False, allow_infinity=False, allow_subnormal=False),
    mu0=st.floats(min_value=0.1, max_value=8.0, allow_nan=False, allow_infinity=False, allow_subnormal=False),
    dt=st.floats(min_value=0.05, max_value=1.0, allow_nan=False, allow_infinity=False, allow_subnormal=False),
)
def test_genealogy_rung2_calibrated_against_uniformization_oracle(
    fast_propagator, k: int, headroom: float, lam0: float, mu0: float, dt: float
):
    """Calibrate Padé and Krylov vertices against strictly non-negative Jensen Uniformization."""
    edge = CapacityEdge(k=k, K=float(k) + headroom)
    n_max = edge.active_ghost_ceiling + 2
    lam_vec = evaluate_capacity_throttle(edge, n_max=n_max, lam0=lam0)
    M = assemble_metzler_generator(k=k, lam_vec=lam_vec, mu0=mu0)

    stiffness = float(np.max(-np.diag(M)) * dt)
    event(f"stiffness_decade={int(math.floor(math.log10(max(stiffness, 1e-6))))}")

    p0 = np.zeros(n_max + 1, dtype=np.float64)
    p0[0] = 1.0

    p_unif = propagate_uniformized(M, p0, dt)
    p_fast = fast_propagator(M, p0, dt)

    l1_defect = float(np.linalg.norm(p_unif - p_fast, ord=1))
    negativity = float(max(0.0, -np.min(p_fast)))

    target(l1_defect, label="rung2_vs_uniformization_l1_defect")
    assert negativity <= 1e-13
    assert l1_defect <= 1e-10 * max(1.0, stiffness)


@settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(
    k=st.integers(min_value=2, max_value=10),
    eps=st.floats(min_value=1e-7, max_value=1e-2, allow_nan=False, allow_infinity=False, allow_subnormal=False),
    lam0=st.floats(min_value=0.2, max_value=4.0, allow_nan=False, allow_infinity=False, allow_subnormal=False),
    mu0=st.floats(min_value=0.05, max_value=3.0, allow_nan=False, allow_infinity=False, allow_subnormal=False),
    dt=st.floats(min_value=0.05, max_value=1.0, allow_nan=False, allow_infinity=False, allow_subnormal=False),
)
def test_vertex_seam_continuity_across_capacity_ceiling(
    fast_propagator, k: int, eps: float, lam0: float, mu0: float, dt: float
):
    """Probe the seam between boundary_grazing (K = k + eps) and saturated_ceiling (K = k - eps)."""
    n_max = 4
    p0 = np.zeros(n_max + 1, dtype=np.float64)
    p0[0] = 1.0
    st0 = BranchingState(t=dt, k=k, P=p0)

    st_below = step_interval_vertex(st0, dt=dt, lam0=lam0, mu0=mu0, K=float(k) - eps, propagator=fast_propagator)
    st_above = step_interval_vertex(st0, dt=dt, lam0=lam0, mu0=mu0, K=float(k) + eps, propagator=fast_propagator)

    seam_jump = float(np.linalg.norm(st_above.P - st_below.P, ord=1))
    target(seam_jump / eps, label="capacity_vertex_seam_lipschitz_ratio")

    obs_below = step_observation_vertex(st_below, lam0=lam0, K=float(k) - eps)
    obs_above = step_observation_vertex(st_above, lam0=lam0, K=float(k) + eps)

    assert obs_below.lnL == -math.inf
    assert np.all(np.isfinite(obs_below.P))
    assert math.isfinite(obs_above.lnL)
    assert seam_jump <= 2.0 * lam0 * k * dt * eps + 1e-12


@settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(
    k=st.integers(min_value=2, max_value=8),
    headroom=st.floats(min_value=0.5, max_value=8.0, allow_nan=False, allow_infinity=False, allow_subnormal=False),
    lam0=st.floats(min_value=0.2, max_value=3.0, allow_nan=False, allow_infinity=False, allow_subnormal=False),
    mu0=st.floats(min_value=0.05, max_value=2.0, allow_nan=False, allow_infinity=False, allow_subnormal=False),
    dt1=st.floats(min_value=0.05, max_value=0.8, allow_nan=False, allow_infinity=False, allow_subnormal=False),
    dt2=st.floats(min_value=0.05, max_value=0.8, allow_nan=False, allow_infinity=False, allow_subnormal=False),
)
def test_vertex_seam_chapman_kolmogorov_interval_splitting(
    fast_propagator, k: int, headroom: float, lam0: float, mu0: float, dt1: float, dt2: float
):
    """Inserting a zero-observation interior vertex at t - dt1 must not alter final state."""
    edge = CapacityEdge(k=k, K=float(k) + headroom)
    n_max = edge.active_ghost_ceiling + 2
    p0 = np.zeros(n_max + 1, dtype=np.float64)
    p0[0] = 1.0
    st0 = BranchingState(t=dt1 + dt2, k=k, P=p0)

    st_single = step_interval_vertex(st0, dt=dt1 + dt2, lam0=lam0, mu0=mu0, K=edge.K, propagator=fast_propagator)
    st_mid = step_interval_vertex(st0, dt=dt1, lam0=lam0, mu0=mu0, K=edge.K, propagator=fast_propagator)
    st_split = step_interval_vertex(st_mid, dt=dt2, lam0=lam0, mu0=mu0, K=edge.K, propagator=fast_propagator)

    split_defect = float(np.linalg.norm(st_single.P - st_split.P, ord=1))
    target(split_defect, label="interior_vertex_splitting_defect")
    assert split_defect <= 1e-12


# ============================================================================
# Stateful Control-Graph Walker Across Vertices
# ============================================================================

class HolonomyVertexMachine(RuleBasedStateMachine):
    @initialize(
        lam0=st.floats(0.3, 3.0, allow_nan=False, allow_infinity=False, allow_subnormal=False),
        mu0=st.floats(0.05, 2.0, allow_nan=False, allow_infinity=False, allow_subnormal=False),
        headroom=st.floats(1.5, 15.0, allow_nan=False, allow_infinity=False, allow_subnormal=False),
    )
    def init_graph(self, lam0: float, mu0: float, headroom: float):
        self.lam0 = lam0
        self.mu0 = mu0
        self.K = 10.0 + headroom
        edge = CapacityEdge(k=2, K=self.K)
        n_max = edge.active_ghost_ceiling + 2
        self.trace = BranchingTrace.initialize(crown_age=20.0, n_max=n_max)

    @rule(dt=st.floats(0.02, 1.0, allow_nan=False, allow_infinity=False, allow_subnormal=False))
    def traverse_interval_vertex(self, dt: float):
        st_next = step_interval_vertex(
            self.trace.current,
            dt=dt,
            lam0=self.lam0,
            mu0=self.mu0,
            K=self.K,
            propagator=propagate_dense_pade,
        )
        self.trace = self.trace.append(st_next)

    @rule()
    def traverse_observation_vertex(self):
        edge = CapacityEdge(k=self.trace.current.k, K=self.K)
        if edge.regime == "saturated_ceiling":
            return
        st_next = step_observation_vertex(self.trace.current, lam0=self.lam0, K=self.K)
        if math.isfinite(st_next.lnL):
            self.trace = self.trace.append(st_next)

    @rule()
    def traverse_rollback_vertex(self):
        if len(self.trace.states) > 1:
            self.trace = self.trace.rollback(steps=1)

    @invariant()
    def verify_all_vertices_preserve_contracts(self):
        curr = self.trace.current
        assert not curr.P.flags.writeable
        assert np.all(np.isfinite(curr.P))
        assert float(np.min(curr.P)) >= -1e-13
        assert math.isfinite(curr.lnL)
        assert self.trace.states[0].P[0] == 1.0


TestHolonomyVertices = HolonomyVertexMachine.TestCase
