"""Continuous-time Master Equation solver for Diversity-Dependent Diversification (Etienne 2012).

Solves the exact continuous-time Markov master equation P(n, t) for cladogenesis
under carrying-capacity saturation:
    lambda(n) = max(0, lambda_0 * (1 - n/K))
    mu(n) = mu_0

Replaces random-walk MCMC approximations with exact matrix exponential and ODE integration.
Supports exact log-likelihood evaluation of branching times conditioning on survival and crown age.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Sequence, Tuple

import numpy as np
from scipy.integrate import solve_ivp
from scipy.linalg import expm


@dataclass(frozen=True)
class MasterEquationParams:
    """Parameters for diversity-dependent diversification master equation."""

    lambda0: float  # Baseline speciation rate (Myr^-1)
    mu0: float      # Baseline extinction rate (Myr^-1)
    K: float        # Clade carrying capacity (K species ceiling)
    max_richness: int = 50
    dd_model: float = 1.3  # 1.3: linear to K; 1.0: linear to (lambda - mu)

    def __post_init__(self) -> None:
        if self.lambda0 <= 0.0:
            raise ValueError(f"lambda0 must be > 0.0, got {self.lambda0}")
        if self.mu0 < 0.0:
            raise ValueError(f"mu0 must be >= 0.0, got {self.mu0}")
        if self.K <= 0.0:
            raise ValueError(f"Carrying capacity K must be > 0.0, got {self.K}")


def construct_transition_matrix(params: MasterEquationParams) -> np.ndarray:
    """Build tridiagonal transition rate matrix Q for master equation dP/dt = Q * P.

    State space: n in [0, max_richness]
    Transition rates:
      n -> n + 1: lambda(n) * n
      n -> n - 1: mu(n) * n
    """
    N = params.max_richness + 1
    Q = np.zeros((N, N), dtype=np.float64)

    for n in range(N):
        # Speciation transition: n -> n + 1
        if n < params.max_richness and n > 0:
            lam_n = max(0.0, params.lambda0 * (1.0 - n / params.K))
            rate_up = lam_n * n
            Q[n + 1, n] += rate_up
            Q[n, n] -= rate_up

        # Extinction transition: n -> n - 1
        if n > 0:
            rate_down = params.mu0 * n
            Q[n - 1, n] += rate_down
            Q[n, n] -= rate_down

    return Q


def solve_master_equation(
    params: MasterEquationParams,
    initial_richness: int = 1,
    time_span: float = 10.0,
    num_eval_points: int = 101,
) -> Tuple[np.ndarray, np.ndarray]:
    """Integrate dP/dt = Q * P from t=0 to time_span.

    Returns:
        times: (T,) array of time points
        probabilities: (max_richness + 1, T) array of state probabilities
    """
    Q = construct_transition_matrix(params)
    N = params.max_richness + 1

    P0 = np.zeros(N, dtype=np.float64)
    P0[initial_richness] = 1.0

    def rhs(t: float, P: np.ndarray) -> np.ndarray:
        return Q @ P

    t_eval = np.linspace(0.0, time_span, num_eval_points)
    sol = solve_ivp(rhs, (0.0, time_span), P0, t_eval=t_eval, method="RK45")

    return sol.t, sol.y


def _build_etienne_generator_matrix(
    la: float, mu: float, k_cap: float, lx: int, k_lineages: int, dd_model: float = 1.3
) -> np.ndarray:
    """Build tridiagonal generator matrix M for unobserved lineages during interval k."""
    nvec = np.arange(lx, dtype=float)
    if dd_model == 1.3:
        lavec = np.maximum(0.0, la * (1.0 - (nvec + k_lineages) / k_cap))
        muvec = np.full(lx, mu, dtype=float)
    else:
        lavec = np.maximum(0.0, la - (la - mu) * (nvec + k_lineages) / k_cap)
        muvec = np.full(lx, mu, dtype=float)

    m_matrix = np.zeros((lx, lx), dtype=float)
    for j in range(lx - 1):
        m_matrix[j + 1, j] = lavec[j] * (nvec[j] + 2.0 * k_lineages)
    for j in range(1, lx):
        m_matrix[j - 1, j] = muvec[j] * nvec[j]
    for j in range(lx):
        m_matrix[j, j] = -(lavec[j] + muvec[j]) * (nvec[j] + k_lineages)
    m_matrix[lx - 1, lx - 1] = -muvec[lx - 1] * (nvec[lx - 1] + k_lineages)
    return m_matrix


def compute_etienne_branching_loglik(
    params: MasterEquationParams,
    branching_times: Sequence[float],
    condition_on_survival: bool = True,
    soc: int = 2,  # 2 for crown age, 1 for stem age
) -> float:
    """Compute exact log-likelihood of branching times under Etienne's master equation.

    Parameters
    ----------
    params : MasterEquationParams
        Model parameters (lambda0, mu0, K).
    branching_times : Sequence[float]
        Branching times in Myr before present (positive, descending).
    condition_on_survival : bool
        If True, condition on clade surviving to present.
    soc : int
        2 for crown age, 1 for stem age.
    """
    brts = np.sort(np.abs(np.asarray(branching_times, dtype=float)))[::-1]
    if len(brts) == 0:
        return -np.inf
    if brts[-1] != 0.0:
        brts = np.append(brts, 0.0)

    s_species = len(brts) - 1 + (soc - 2)
    if s_species < 1:
        return -np.inf

    k_cap = params.K
    if s_species > math.ceil(k_cap) and params.dd_model == 1.3:
        return -np.inf

    lx = int(math.ceil(k_cap)) + 4
    loglik = math.lgamma(s_species)

    probs = np.zeros(lx, dtype=float)
    probs[0] = 1.0

    la = params.lambda0
    mu = params.mu0

    for k_idx in range(1, s_species + 2 - soc):
        k1 = k_idx + (soc - 2)
        dt = abs(brts[k_idx] - brts[k_idx - 1])
        if dt > 0:
            m_mat = _build_etienne_generator_matrix(la, mu, k_cap, lx, k1, params.dd_model)
            probs = expm(m_mat * dt).dot(probs)

        if k_idx < (s_species + 2 - soc):
            nvec = np.arange(lx, dtype=float)
            if params.dd_model == 1.3:
                lavec = np.maximum(0.0, la * (1.0 - (nvec + k1) / k_cap))
            else:
                lavec = np.maximum(0.0, la - (la - mu) * (nvec + k1) / k_cap)
            probs = lavec * probs
            s_p = float(np.sum(probs))
            if s_p <= 0.0 or np.isnan(s_p):
                return -np.inf
            loglik += math.log(s_p)
            probs /= s_p

    p0 = float(probs[0])
    if p0 <= 0.0 or np.isnan(p0):
        return -np.inf
    loglik += math.log(p0)
    loglik -= math.lgamma(s_species + 1)

    if condition_on_survival:
        probsn = np.zeros(lx, dtype=float)
        probsn[0] = 1.0
        dt_total = abs(brts[0] - brts[-1])
        m_mat_total = _build_etienne_generator_matrix(la, mu, k_cap, lx, soc, params.dd_model)
        probsn = expm(m_mat_total * dt_total).dot(probsn)
        nvec = np.arange(lx, dtype=float)
        if soc == 2:
            aux = (nvec + 2.0) * (nvec + 3.0) / 6.0
        else:
            aux = nvec + 1.0
        probsc = probsn / aux
        norm_sum = float(np.sum(probsc))
        if norm_sum <= 0.0 or np.isnan(norm_sum):
            return -np.inf
        loglik -= math.log(norm_sum)

    return float(loglik)


def profile_etienne_k(
    branching_times: Sequence[float],
    k_grid: Sequence[float],
    fixed_lambda0: float = 1.2,
    fixed_mu0: float = 0.1,
    soc: int = 2,
) -> Tuple[np.ndarray, np.ndarray]:
    """Compute profile log-likelihood across carrying capacity K."""
    lls = []
    for k in k_grid:
        p = MasterEquationParams(
            lambda0=fixed_lambda0,
            mu0=fixed_mu0,
            K=k,
        )
        ll = compute_etienne_branching_loglik(p, branching_times, condition_on_survival=True, soc=soc)
        lls.append(ll)
    return np.array(k_grid, dtype=float), np.array(lls, dtype=float)
