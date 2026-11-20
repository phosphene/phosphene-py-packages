"""holonomy.macroevo.escalation - Numerical genealogy (Rung 0..3) and Kneebone Background Realization.

Organizes macroevolutionary diversification solvers along the 4-tier Python numerical genealogy:
- Rung 0: Pure ``math`` scalar closed forms (pure-death decay, Nee-May-Harvey constant-rate birth-death).
- Rung 1: Read-only 1D ``numpy`` capacity-throttled rate vectors via ``CapacityEdge``.
- Rung 2: Coupled linear Metzler semigroups (Padé ``expm``, sparse Krylov ``expm_multiply``,
  calibrated against Jensen's strictly non-negative Uniformization oracle).
- Rung 3: Capacity-bounded non-abelian path evolution (continuous interval vertices interleaved
  with discrete cladogenetic split vertices) paired with the Kneebone Background Realization.
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

from phosphene.holonomy.core.capacity import CapacityEdge, capacity_throttle

Propagator = Callable[[np.ndarray, np.ndarray, float], np.ndarray]


# ============================================================================
# Core Immutable State & Lineage Primitives
# ============================================================================

@dataclass(frozen=True)
class BranchingState:
    """Immutable state snapshot for continuous branching and unobserved lineage distribution.

    Dimensions:
        t: [T] Current age before present.
        k: [lineages] Observed standing lineage count.
        P: Read-only float64 array of unobserved lineage probabilities P(j), j = 0..n_max.
        lnL: [nats] Accumulated log-evidence up to this vertex.
    """

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
    def initialize(cls, crown_age: float, n_max: int, initial_k: int = 2) -> BranchingTrace:
        p0 = np.zeros(n_max + 1, dtype=np.float64)
        p0[0] = 1.0
        return cls(states=(BranchingState(t=crown_age, k=initial_k, P=p0, lnL=0.0),))

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
    """Pure-death survival log-probability for k lineages over interval dt.

    Genealogy:
        Rung: 0 (Scalar closed-form; stdlib ``math`` only, zero arrays).
        Collapses From: Rung 2 Metzler semigroup when ``lam0 == 0.0``.
        Literature: Kendall (1948).

    Objective:
        ln P_0(dt) = -k * mu0 * dt

    Dimensions:
        dt: [T] Interval duration (>= 0).
        k: [lineages] Standing observed lineages (>= 0).
        mu0: [T^-1] Extinction rate (>= 0).
        Returns: [nats] Log survival probability <= 0.
    """
    return -float(k) * mu0 * dt


def rung0_constant_rate_loglik(
    branching_times: Sequence[float],
    lam0: float,
    mu0: float,
) -> float:
    """Constant-rate linear birth-death log-likelihood (Nee-May-Harvey closed form as K -> inf).

    Genealogy:
        Rung: 0 (Scalar closed-form; stdlib ``math`` only, zero arrays).
        Collapses From: Rung 3 capacity-bounded branching likelihood as K -> inf.
        Literature: Nee, May, & Harvey (1994) Phil. Trans. R. Soc. B 344:305–311.

    Objective:
        ln L = (s - 1) ln(lam0) + 2 ln p_1(t_1) + sum_{i=2}^s ln p_1(t_i)
        p_1(t) = r^2 exp(-r t) / (lam0 - mu0 exp(-r t))^2,  r = lam0 - mu0

    Dimensions:
        branching_times: [T] Descending crown branching times (t_1 > ... > t_s > 0).
        lam0, mu0: [T^-1] Baseline speciation (> 0) and extinction (>= 0) rates.
        Returns: [nats] Constant-rate log-likelihood.
    """
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

def metzler_generator(
    k: int,
    lam_vec: np.ndarray,
    mu0: float,
    reflect_top: bool = False,
) -> np.ndarray:
    """Tridiagonal Metzler generator matrix M_k for unobserved lineages j = 0..n_max.

    Genealogy:
        Rung: 1/2 (Read-only 2D ``numpy`` Metzler matrix; off-diagonals strictly >= 0).
        Literature: Etienne et al. (2012) Proc. R. Soc. B 279:1300–1309.

    Objective:
        M[j+1, j] = lam_vec[j] * (2k + j)
        M[j-1, j] = mu0 * j
        M[j, j]   = -(lam_vec[j] + mu0) * (k + j)

    Dimensions:
        k: [lineages] Observed standing lineages (>= 0).
        lam_vec: [T^-1] 1D array of throttled speciation rates for j = 0..n_max.
        mu0: [T^-1] Constant extinction rate (>= 0).
        Returns: Read-only (n_max+1, n_max+1) float64 Metzler matrix [T^-1].
    """
    n_max = lam_vec.shape[0] - 1
    j = np.arange(n_max + 1, dtype=np.float64)
    diag = -(lam_vec + mu0) * (k + j)
    if reflect_top:
        diag[-1] = -mu0 * (k + j[-1])
    sub = lam_vec[:-1] * (2.0 * k + j[:-1])
    sup = mu0 * j[1:]
    M = np.diag(diag) + np.diag(sub, k=-1) + np.diag(sup, k=1)
    M.flags.writeable = False
    return M


# Backward-compatibility alias
assemble_metzler_generator = metzler_generator


def propagate_uniformized(M: np.ndarray, P: np.ndarray, dt: float) -> np.ndarray:
    """Propagate state vector via Jensen's Uniformization oracle (strictly non-negative).

    Genealogy:
        Rung: 2 calibration oracle (Poisson-weighted powers of non-negative Q = I + M / gamma).
        Literature: Jensen (1953); Grassmann (1977).

    Objective:
        exp(M dt) P = sum_{m=0}^{m_cut} Pois(m; gamma dt) Q^m P,   gamma = max_i (-M_ii)

    Invariants & Oracles:
        - Strictly non-negative output for any Metzler matrix M and non-negative P.
        - Serves as the reference oracle calibrating Padé and Krylov propagators in stiff regimes.
    """
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
# Rung 3: Vertex Transitions & Kneebone Background Realization
# ============================================================================

def step_interval_vertex(
    st_curr: BranchingState,
    dt: float,
    lam0: float,
    mu0: float,
    K: float,
    propagator: Propagator = propagate_dense_pade,
    dd_model: float = 1.3,
    reflect_top: bool = False,
) -> BranchingState:
    """Propagate unobserved distribution across a continuous time interval (dt >= 0).

    Genealogy:
        Rung: 3 continuous interval vertex built on ``CapacityEdge`` + ``metzler_generator``.
        Collapses To: Rung 0 pure-death decay ``exp(-k * mu0 * dt)`` when ``lam0 == 0``.
    """
    edge = CapacityEdge(k=st_curr.k, K=K)
    n_max = st_curr.P.shape[0] - 1
    lam_vec = capacity_throttle(edge, n_max=n_max, lam0=lam0, mu0=mu0, dd_model=dd_model)
    M = metzler_generator(k=st_curr.k, lam_vec=lam_vec, mu0=mu0, reflect_top=reflect_top)
    p_next = propagator(M, st_curr.P, dt)
    return BranchingState(t=st_curr.t - dt, k=st_curr.k, P=p_next, lnL=st_curr.lnL)


def step_observation_vertex(
    st_curr: BranchingState,
    lam0: float,
    K: float,
    mu0: float = 0.0,
    dd_model: float = 1.3,
) -> BranchingState:
    """Condition state at an observed cladogenetic split vertex (t = t_s).

    Genealogy:
        Rung: 3 discrete observation vertex interleaved with ``step_interval_vertex``.

    Boundary & Falsification Semantics:
        - When total split evidence <= 0.0 (e.g. saturated_ceiling), returns immutable
          BranchingState with zeroed P and ``lnL = -math.inf`` (never 0/0 NaN).
    """
    edge = CapacityEdge(k=st_curr.k, K=K)
    n_max = st_curr.P.shape[0] - 1
    lam_vec = capacity_throttle(edge, n_max=n_max, lam0=lam0, mu0=mu0, dd_model=dd_model)
    weighted = lam_vec * st_curr.P
    evidence = float(np.sum(weighted))
    if evidence <= 0.0 or not math.isfinite(evidence):
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
    """Kneebone Background Realization comparing Rung 3 capacity dynamics against Rung 0 closed form.

    Serves as an exact, invariant touch-point reporting ``delta_loglik = lnL_rung3 - lnL_rung0``
    and the bottleneck ``CapacityEdge.regime`` without imposing gating or prescribing modeling choices.
    """

    rung0_loglik: float
    rung3_loglik: float
    delta_loglik: float
    bottleneck_regime: str

    @property
    def escalation_gain(self) -> float:
        """Backward-compatibility alias for ``delta_loglik``."""
        return self.delta_loglik


# Backward-compatibility alias
ScientistEscalationReport = BackgroundRealizationReport


def background_realization(
    branching_times: Sequence[float],
    lam0: float,
    mu0: float,
    K: float,
    propagator: Propagator = propagate_dense_pade,
) -> BackgroundRealizationReport:
    """Pairwise Kneebone Background Realization across Rung 0 closed form and Rung 3 capacity dynamics.

    Genealogy:
        Rung: 0 + 3 comparative touch-point.
        Collapses To: ``delta_loglik -> 0.0`` as ``K -> inf``.
        Literature: Kneebone (1963); Nee, May, & Harvey (1994); Etienne et al. (2012).

    Objective:
        delta_loglik = ln L_rung3(brts | lam0, mu0, K) - ln L_rung0(brts | lam0, mu0)

    Dimensions:
        branching_times: [T] Crown branching times (> 0).
        lam0, mu0: [T^-1] Baseline speciation (> 0) and extinction (>= 0) rates.
        K: [lineages] Carrying capacity ceiling (> 0).
        Returns: ``BackgroundRealizationReport``.
    """
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
    trace = BranchingTrace.initialize(crown_age=times[0], n_max=n_max, initial_k=2)

    for idx in range(len(times) - 1):
        dt = times[idx] - times[idx + 1]
        trace = trace.append(
            step_interval_vertex(trace.current, dt=dt, lam0=lam0, mu0=mu0, K=K, propagator=propagator)
        )
        if idx < len(brts) - 1:
            trace = trace.append(
                step_observation_vertex(trace.current, lam0=lam0, K=K)
            )

    p0_final = float(trace.current.P[0])
    if p0_final <= 0.0 or not math.isfinite(p0_final) or not math.isfinite(trace.current.lnL):
        lnL_r3 = -math.inf
        gain = -math.inf
    else:
        lnL_r3 = trace.current.lnL + math.log(p0_final)
        gain = lnL_r3 - lnL_r0

    return BackgroundRealizationReport(
        rung0_loglik=lnL_r0,
        rung3_loglik=lnL_r3,
        delta_loglik=gain,
        bottleneck_regime=bottleneck.regime,
    )


# Backward-compatibility aliases
evaluate_with_background_realization = background_realization
evaluate_with_escalation_ladder = background_realization

__all__ = [
    "Propagator",
    "BranchingState",
    "BranchingTrace",
    "rung0_pure_death_logprob",
    "rung0_constant_rate_loglik",
    "metzler_generator",
    "assemble_metzler_generator",
    "propagate_uniformized",
    "propagate_dense_pade",
    "propagate_sparse_krylov",
    "step_interval_vertex",
    "step_observation_vertex",
    "BackgroundRealizationReport",
    "ScientistEscalationReport",
    "background_realization",
    "evaluate_with_background_realization",
    "evaluate_with_escalation_ladder",
]
