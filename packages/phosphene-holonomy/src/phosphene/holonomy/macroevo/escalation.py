"""holonomy.macroevo.escalation - Numerical genealogy and scientist escalation ladder.

Implements Rung 0 (pure math closed form) through Rung 3 (capacity-bounded matrix semigroup),
calibrated against Jensen's uniformization oracle and enabling empirical model escalation reporting.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Callable, Sequence, Tuple
import numpy as np
from scipy.linalg import expm
from scipy.sparse import diags
from scipy.sparse.linalg import expm_multiply
from scipy.stats import poisson

from phosphene.holonomy.core.capacity import CapacityEdge, evaluate_capacity_throttle


# ============================================================================
# Core Immutable State & Lineage Primitives
# ============================================================================

@dataclass(frozen=True)
class BranchingState:
    """Immutable state snapshot for continuous branching and unobserved lineage distribution."""

    t: float
    k: int
    P: np.ndarray
    lnL: float = 0.0

    def __post_init__(self) -> None:
        buf = np.array(self.P, dtype=np.float64, copy=True)
        buf.flags.writeable = False
        object.__setattr__(self, "P", buf)


@dataclass(frozen=True)
class BranchingTrace:
    """Ordered, append-only lineage of immutable BranchingState snapshots."""

    states: Tuple[BranchingState, ...]

    @classmethod
    def initialize(cls, crown_age: float, n_max: int) -> BranchingTrace:
        p0 = np.zeros(n_max + 1, dtype=np.float64)
        p0[0] = 1.0
        return cls(states=(BranchingState(t=crown_age, k=2, P=p0, lnL=0.0),))

    @property
    def current(self) -> BranchingState:
        return self.states[-1]

    def append(self, next_st: BranchingState) -> BranchingTrace:
        return BranchingTrace(states=self.states + (next_st,))

    def rollback(self, steps: int = 1) -> BranchingTrace:
        if steps <= 0 or steps >= len(self.states):
            raise ValueError("Invalid rollback step count")
        return BranchingTrace(states=self.states[:-steps])


# ============================================================================
# Rung 0: Scalar Closed-Form Primitives (math Standard Library, Zero Arrays)
# ============================================================================

def rung0_pure_death_logprob(dt: float, k: int, mu0: float) -> float:
    """Pure-death decay log-probability: ln P_0(t) = -k * mu0 * dt."""
    return -float(k) * mu0 * dt


def rung0_constant_rate_loglik(
    branching_times: Sequence[float], lam0: float, mu0: float
) -> float:
    """Constant-rate linear birth-death log-likelihood (Nee-May-Harvey closed form as K -> inf)."""
    r = lam0 - mu0
    s = len(branching_times)
    total = (s - 1) * math.log(lam0)
    for idx, t in enumerate(branching_times):
        if abs(r) < 1e-9:
            log_p1 = -2.0 * math.log1p(lam0 * t)
        else:
            exp_rt = math.exp(-r * t)
            denom = abs(lam0 - mu0 * exp_rt)
            log_p1 = 2.0 * math.log(abs(r)) - r * t - 2.0 * math.log(denom)
        total += (2.0 * log_p1) if idx == 0 else log_p1
    return total


# ============================================================================
# Rung 1 & 2: Metzler Generator & Propagator Vertices
# ============================================================================

def assemble_metzler_generator(k: int, lam_vec: np.ndarray, mu0: float) -> np.ndarray:
    """Assemble tridiagonal Metzler matrix M_k for unobserved lineages."""
    n_max = lam_vec.shape[0] - 1
    j = np.arange(n_max + 1, dtype=np.float64)
    diag = -(lam_vec + mu0) * (k + j)
    sub = lam_vec[:-1] * (2.0 * k + j[:-1])
    sup = mu0 * j[1:]
    M = np.diag(diag) + np.diag(sub, k=-1) + np.diag(sup, k=1)
    M.flags.writeable = False
    return M


def propagate_uniformized(M: np.ndarray, P: np.ndarray, dt: float) -> np.ndarray:
    """Propagate via Jensen's Uniformization oracle (strictly non-negative)."""
    gamma = float(np.max(-np.diag(M)))
    if gamma == 0.0 or dt == 0.0:
        return P.copy()
    Q = np.eye(M.shape[0], dtype=np.float64) + M / gamma
    lam_dt = gamma * dt
    m_cut = int(math.ceil(lam_dt + 12.0 * math.sqrt(max(lam_dt, 1.0)) + 20))
    weights = poisson.pmf(np.arange(m_cut + 1), lam_dt)
    term = P.copy()
    acc = weights[0] * term
    for m in range(1, m_cut + 1):
        term = Q @ term
        acc += weights[m] * term
    return acc


def propagate_dense_pade(M: np.ndarray, P: np.ndarray, dt: float) -> np.ndarray:
    """Propagate via scaling-and-squaring Padé matrix exponential (scipy.linalg.expm)."""
    if dt == 0.0:
        return P.copy()
    return expm(M * dt) @ P


def propagate_sparse_krylov(M: np.ndarray, P: np.ndarray, dt: float) -> np.ndarray:
    """Propagate via sparse Krylov subspace matrix exponential (scipy.sparse.linalg.expm_multiply)."""
    if dt == 0.0:
        return P.copy()
    M_csc = diags(
        [np.diag(M, -1), np.diag(M, 0), np.diag(M, 1)],
        offsets=[-1, 0, 1],
        format="csc",
    )
    return expm_multiply(M_csc * dt, P)


# ============================================================================
# Rung 3: Vertex Transitions & Escalation Ladder Report
# ============================================================================

def step_interval_vertex(
    st_curr: BranchingState,
    dt: float,
    lam0: float,
    mu0: float,
    K: float,
    propagator: Callable[[np.ndarray, np.ndarray, float], np.ndarray] = propagate_dense_pade,
) -> BranchingState:
    """Propagate unobserved distribution across a continuous time interval (dt > 0)."""
    edge = CapacityEdge(k=st_curr.k, K=K)
    n_max = st_curr.P.shape[0] - 1
    lam_vec = evaluate_capacity_throttle(edge, n_max=n_max, lam0=lam0)
    M = assemble_metzler_generator(k=st_curr.k, lam_vec=lam_vec, mu0=mu0)
    p_next = propagator(M, st_curr.P, dt)
    return BranchingState(t=st_curr.t - dt, k=st_curr.k, P=p_next, lnL=st_curr.lnL)


def step_observation_vertex(st_curr: BranchingState, lam0: float, K: float) -> BranchingState:
    """Update state at an observed cladogenetic split vertex (t = t_s)."""
    edge = CapacityEdge(k=st_curr.k, K=K)
    n_max = st_curr.P.shape[0] - 1
    lam_vec = evaluate_capacity_throttle(edge, n_max=n_max, lam0=lam0)
    weighted = lam_vec * st_curr.P
    evidence = float(np.sum(weighted))
    if evidence <= 0.0:
        return BranchingState(
            t=st_curr.t,
            k=st_curr.k + 1,
            P=np.zeros_like(st_curr.P),
            lnL=-math.inf,
        )
    return BranchingState(
        t=st_curr.t,
        k=st_curr.k + 1,
        P=weighted / evidence,
        lnL=st_curr.lnL + math.log(evidence),
    )


@dataclass(frozen=True)
class BackgroundRealizationReport:
    """Evaluates higher-order dynamics against the Rung 0 analytical background realization.

    Serves as an exact, invariant touch-point (Kneebone background realization)
    reporting the empirical log-likelihood delta without imposing gating thresholds
    or prescribing modeling choices.
    """

    rung0_loglik: float
    rung3_loglik: float
    delta_loglik: float
    bottleneck_regime: str

    @property
    def escalation_gain(self) -> float:
        """Alias for delta_loglik."""
        return self.delta_loglik


# Backward compatibility alias
ScientistEscalationReport = BackgroundRealizationReport


def evaluate_with_background_realization(
    branching_times: Sequence[float],
    lam0: float,
    mu0: float,
    K: float,
    propagator: Callable[[np.ndarray, np.ndarray, float], np.ndarray] = propagate_dense_pade,
) -> BackgroundRealizationReport:
    """Pairwise evaluation across Rung 0 background realization and Rung 3 dynamics."""
    brts = tuple(sorted(branching_times, reverse=True))
    lnL_r0 = rung0_constant_rate_loglik(brts, lam0=lam0, mu0=mu0)

    k_max = len(brts) + 1
    bottleneck = CapacityEdge(k=k_max, K=K)
    if bottleneck.regime == "saturated_ceiling":
        return BackgroundRealizationReport(
            rung0_loglik=lnL_r0,
            rung3_loglik=-math.inf,
            delta_loglik=-math.inf,
            bottleneck_regime=bottleneck.regime,
        )

    n_max = min(max(bottleneck.active_ghost_ceiling + 4, 25), 120)
    times = list(brts) + [0.0]
    trace = BranchingTrace.initialize(crown_age=times[0], n_max=n_max)

    for idx in range(len(times) - 1):
        dt = times[idx] - times[idx + 1]
        trace = trace.append(
            step_interval_vertex(trace.current, dt=dt, lam0=lam0, mu0=mu0, K=K, propagator=propagator)
        )
        if idx < len(brts) - 1:
            trace = trace.append(
                step_observation_vertex(trace.current, lam0=lam0, K=K)
            )

    lnL_r3 = trace.current.lnL + math.log(max(float(trace.current.P[0]), 1e-300))
    gain = lnL_r3 - lnL_r0
    return BackgroundRealizationReport(
        rung0_loglik=lnL_r0,
        rung3_loglik=lnL_r3,
        delta_loglik=gain,
        bottleneck_regime=bottleneck.regime,
    )


# Backward compatibility alias
evaluate_with_escalation_ladder = evaluate_with_background_realization
