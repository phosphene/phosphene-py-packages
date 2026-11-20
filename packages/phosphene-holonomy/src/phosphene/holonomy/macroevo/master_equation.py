"""Unified Continuous-Time Master Equation Solver for Diversity-Dependent Diversification (Etienne 2012).

Built directly on ``holonomy.core.capacity.CapacityEdge`` and ``holonomy.macroevo.escalation``
(``BranchingState``, ``BranchingTrace``, ``metzler_generator``, and pluggable propagators:
Padé, sparse Krylov, and Jensen Uniformization). Zero duplicate generator logic.

Genealogy:
    Rung: 2 (full richness distribution dP/dt = Q P) and Rung 3 (capacity-bounded
        branching likelihood with survival conditioning and soc in {1, 2}).
    Literature: Etienne et al. (2012) Proc. R. Soc. B 279:1300–1309.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Sequence, Tuple

import numpy as np
from scipy.integrate import solve_ivp

from phosphene.holonomy.core.capacity import CapacityEdge, capacity_throttle
from phosphene.holonomy.macroevo.escalation import (
    BranchingTrace,
    Propagator,
    metzler_generator,
    propagate_dense_pade,
    step_interval_vertex,
    step_observation_vertex,
)


@dataclass(frozen=True)
class MasterEquationParams:
    """Parameters for diversity-dependent diversification master equation.

    Dimensions:
        lambda0: [T^-1] Baseline speciation rate (> 0).
        mu0: [T^-1] Baseline extinction rate (>= 0).
        K: [lineages] Carrying capacity ceiling (> 0).
        max_richness: [lineages] Truncation state space for forward ODE solution.
        dd_model: 1.3 (linear speciation drop to 0 at K) or 1.0 (linear to lambda0 - mu0).
    """

    lambda0: float
    mu0: float
    K: float
    max_richness: int = 50
    dd_model: float = 1.3

    def __post_init__(self) -> None:
        if not math.isfinite(self.lambda0) or self.lambda0 <= 0.0:
            raise ValueError(f"lambda0 must be finite and > 0.0, got {self.lambda0}")
        if not math.isfinite(self.mu0) or self.mu0 < 0.0:
            raise ValueError(f"mu0 must be finite and >= 0.0, got {self.mu0}")
        if not math.isfinite(self.K) or self.K <= 0.0:
            raise ValueError(f"Carrying capacity K must be finite and > 0.0, got {self.K}")


def transition_matrix(params: MasterEquationParams) -> np.ndarray:
    """Tridiagonal forward transition rate matrix Q for dP/dt = Q P on n in [0, max_richness].

    Genealogy:
        Rung: 2 (Read-only 2D ``numpy`` Metzler matrix with zero column sums).

    Objective:
        Q[n+1, n] = n * lambda(n),   Q[n-1, n] = n * mu0,   Q[n, n] = -(Q[n+1, n] + Q[n-1, n])

    Dimensions:
        Returns: Read-only (max_richness + 1, max_richness + 1) float64 matrix [T^-1].
    """
    edge = CapacityEdge(k=0, K=params.K)
    lam_vec = capacity_throttle(
        edge,
        n_max=params.max_richness,
        lam0=params.lambda0,
        mu0=params.mu0,
        dd_model=params.dd_model,
    )
    N = params.max_richness + 1
    Q = np.zeros((N, N), dtype=np.float64)

    for n in range(1, N):
        if n < params.max_richness:
            rate_up = float(lam_vec[n]) * n
            Q[n + 1, n] += rate_up
            Q[n, n] -= rate_up
        rate_down = params.mu0 * n
        Q[n - 1, n] += rate_down
        Q[n, n] -= rate_down

    Q.flags.writeable = False
    return Q


def master_equation_solution(
    params: MasterEquationParams,
    initial_richness: int = 1,
    time_span: float = 10.0,
    num_eval_points: int = 101,
) -> Tuple[np.ndarray, np.ndarray]:
    """Forward solution of dP/dt = Q P over [0, time_span].

    Genealogy:
        Rung: 2 (Continuous-time Markov ODE integration via RK45).

    Dimensions:
        Returns: Read-only ``(times, probabilities)`` arrays of shapes ``(T,)`` and ``(max_richness+1, T)``.
    """
    Q = transition_matrix(params)
    N = params.max_richness + 1
    P0 = np.zeros(N, dtype=np.float64)
    P0[initial_richness] = 1.0

    t_eval = np.linspace(0.0, time_span, num_eval_points)
    sol = solve_ivp(lambda _t, P: Q @ P, (0.0, time_span), P0, t_eval=t_eval, method="RK45")
    t_out = np.array(sol.t, dtype=np.float64, copy=True)
    y_out = np.array(sol.y, dtype=np.float64, copy=True)
    t_out.flags.writeable = False
    y_out.flags.writeable = False
    return t_out, y_out


def branching_loglik(
    params: MasterEquationParams,
    branching_times: Sequence[float],
    condition_on_survival: bool = True,
    soc: int = 2,
    propagator: Propagator = propagate_dense_pade,
) -> float:
    """Exact log-likelihood of branching times under Etienne (2012) master equation.

    Genealogy:
        Rung: 3 (Unified ``CapacityEdge`` + ``BranchingTrace`` + pluggable ``propagator``).
        Collapses To: Constant-rate birth-death likelihood as K -> inf.
        Literature: Etienne et al. (2012) Proc. R. Soc. B 279:1300–1309.

    Objective:
        Interleaves continuous Metzler propagation ``exp(M_k dt)`` and cladogenetic
        observation conditioning ``diag(lam_vec)``, optionally conditioned on clade
        survival to present under stem (soc=1) or crown (soc=2) age.

    Dimensions:
        params: MasterEquationParams (lambda0 [T^-1], mu0 [T^-1], K [lineages]).
        branching_times: [T] Positive branching times before present.
        Returns: [nats] Exact log-likelihood, or ``-math.inf`` when S > ceil(K).

    Boundary & Falsification Semantics:
        - Empty branching_times or S > ceil(K) under dd_model == 1.3 -> returns ``-math.inf``
          (exact model falsification, never a crash).
    """
    brts = np.sort(np.abs(np.asarray(branching_times, dtype=np.float64)))[::-1]
    if len(brts) == 0:
        return -math.inf
    if brts[-1] != 0.0:
        brts = np.append(brts, 0.0)

    s_species = len(brts) - 1 + (soc - 2)
    if s_species < 1:
        return -math.inf

    k_cap = params.K
    if s_species > math.ceil(k_cap) and params.dd_model == 1.3:
        return -math.inf

    lx = int(math.ceil(k_cap)) + 4
    n_max = lx - 1
    initial_k = 1 + (soc - 2)
    trace = BranchingTrace.initialize(crown_age=float(brts[0]), n_max=n_max, initial_k=initial_k)

    num_intervals = s_species + 1 - soc
    for k_idx in range(1, s_species + 2 - soc):
        dt = abs(float(brts[k_idx] - brts[k_idx - 1]))
        if dt > 0.0:
            trace = trace.append(
                step_interval_vertex(
                    trace.current,
                    dt=dt,
                    lam0=params.lambda0,
                    mu0=params.mu0,
                    K=k_cap,
                    propagator=propagator,
                    dd_model=params.dd_model,
                    reflect_top=True,
                )
            )
        if k_idx <= num_intervals:
            obs = step_observation_vertex(
                trace.current,
                lam0=params.lambda0,
                K=k_cap,
                mu0=params.mu0,
                dd_model=params.dd_model,
            )
            if not math.isfinite(obs.lnL):
                return -math.inf
            trace = trace.append(obs)

    p0 = float(trace.current.P[0])
    if p0 <= 0.0 or not math.isfinite(p0):
        return -math.inf

    loglik = math.lgamma(s_species) + trace.current.lnL + math.log(p0) - math.lgamma(s_species + 1)

    if condition_on_survival:
        edge_surv = CapacityEdge(k=soc, K=k_cap)
        lam_surv = capacity_throttle(
            edge_surv,
            n_max=n_max,
            lam0=params.lambda0,
            mu0=params.mu0,
            dd_model=params.dd_model,
        )
        m_total = metzler_generator(k=soc, lam_vec=lam_surv, mu0=params.mu0, reflect_top=True)
        p_init = np.zeros(lx, dtype=np.float64)
        p_init[0] = 1.0
        dt_total = abs(float(brts[0] - brts[-1]))
        probsn = propagator(m_total, p_init, dt_total)

        nvec = np.arange(lx, dtype=np.float64)
        aux = ((nvec + 2.0) * (nvec + 3.0) / 6.0) if soc == 2 else (nvec + 1.0)
        norm_sum = float(np.sum(probsn / aux))
        if norm_sum <= 0.0 or not math.isfinite(norm_sum):
            return -math.inf
        loglik -= math.log(norm_sum)

    return float(loglik)


def carrying_capacity_profile(
    branching_times: Sequence[float],
    k_grid: Sequence[float],
    fixed_lambda0: float = 1.2,
    fixed_mu0: float = 0.1,
    soc: int = 2,
    condition_on_survival: bool = True,
    propagator: Propagator = propagate_dense_pade,
) -> Tuple[np.ndarray, np.ndarray]:
    """Deterministic profile log-likelihood curve across a carrying-capacity grid K.

    Genealogy:
        Rung: 3 profile evaluation over ``branching_loglik``.

    Dimensions:
        Returns: Read-only ``(k_array, loglik_array)`` float64 arrays.
    """
    lls = [
        branching_loglik(
            MasterEquationParams(lambda0=fixed_lambda0, mu0=fixed_mu0, K=float(k)),
            branching_times,
            condition_on_survival=condition_on_survival,
            soc=soc,
            propagator=propagator,
        )
        for k in k_grid
    ]
    k_arr = np.array(k_grid, dtype=np.float64)
    ll_arr = np.array(lls, dtype=np.float64)
    k_arr.flags.writeable = False
    ll_arr.flags.writeable = False
    return k_arr, ll_arr


# Backward-compatibility aliases
construct_transition_matrix = transition_matrix
solve_master_equation = master_equation_solution
compute_etienne_branching_loglik = branching_loglik
profile_etienne_k = carrying_capacity_profile

__all__ = [
    "MasterEquationParams",
    "transition_matrix",
    "master_equation_solution",
    "branching_loglik",
    "carrying_capacity_profile",
    "construct_transition_matrix",
    "solve_master_equation",
    "compute_etienne_branching_loglik",
    "profile_etienne_k",
]
