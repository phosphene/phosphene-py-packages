"""Profile likelihood surfaces and likelihood-ratio hypothesis testing for diversification.

Direct, deterministic replacement for PyRate's trans-dimensional MCMC sampler.
Evaluates the continuous diversity-dependent birth-death likelihood surface:
    lambda(D) = lambda_0 * exp(G_l * D)
over lineages-through-time (LTT) empirical diversity curves.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence, Tuple

import numpy as np
from scipy.optimize import minimize_scalar

from phosphene.holonomy.macroevo.primitives import log_diversity_hazard


@dataclass(frozen=True)
class DiversityTrajectory:
    """Lineages-through-time (LTT) diversity curve across discrete intervals."""

    time_bins_myr: np.ndarray       # Boundary points from oldest to youngest
    standing_diversity: np.ndarray  # Estimated standing richness D(t)
    speciation_events: np.ndarray   # Observed branching events in bin

    def __post_init__(self) -> None:
        if len(self.time_bins_myr) != len(self.standing_diversity) + 1:
            raise ValueError("time_bins_myr must have length len(standing_diversity) + 1")
        if len(self.speciation_events) != len(self.standing_diversity):
            raise ValueError("speciation_events must match length of standing_diversity")


@dataclass(frozen=True)
class ProfileLikelihoodSurface:
    """Exact log-likelihood surface over diversity-dependence parameter G_l."""

    g_l_grid: np.ndarray
    profile_log_liks: np.ndarray
    best_g_l: float
    best_lambda0: float
    max_log_lik: float
    null_log_lik: float  # G_l = 0

    @property
    def likelihood_ratio(self) -> float:
        """Likelihood Ratio test statistic Lambda = 2 * (ln L_alt - ln L_null)."""
        return 2.0 * max(0.0, self.max_log_lik - self.null_log_lik)

    @property
    def p_value(self) -> float:
        """Chi-squared p-value with 1 degree of freedom."""
        from scipy.stats import chi2
        return float(1.0 - chi2.cdf(self.likelihood_ratio, df=1))

    @property
    def excludes_zero(self, alpha: float = 0.05) -> bool:
        """Return True if G_l = 0 is rejected at significance level alpha."""
        return self.p_value < alpha


def evaluate_ltt_log_likelihood(
    lambda0: float,
    g_l: float,
    trajectory: DiversityTrajectory,
) -> float:
    """Compute exact Poisson process log-likelihood for speciation events along LTT.

    ln L = sum_i [ k_i * ln(lambda(D_i)) - lambda(D_i) * D_i * Delta t_i ]
    """
    if lambda0 <= 0.0:
        return -1e10

    total_ll = 0.0
    dt_bins = np.abs(np.diff(trajectory.time_bins_myr))

    for k_i, d_i, dt_i in zip(trajectory.speciation_events, trajectory.standing_diversity, dt_bins):
        if d_i <= 0.0:
            continue
        ln_haz = log_diversity_hazard(lambda0, g_l, float(d_i))
        haz = np.exp(ln_haz)
        total_ll += k_i * ln_haz - (haz * d_i * dt_i)

    return float(total_ll)


def compute_profile_likelihood_surface(
    trajectory: DiversityTrajectory,
    g_l_min: float = -0.5,
    g_l_max: float = 0.5,
    num_points: int = 101,
) -> ProfileLikelihoodSurface:
    """Compute deterministic profile likelihood curve across G_l values.

    For each G_l, optimizes lambda_0 via 1D bounded scalar minimization.
    Replaces PyRate MCMC chains with exact, reproducible likelihood metrics.
    """
    g_grid = np.linspace(g_l_min, g_l_max, num_points)
    profile_lls = []
    opt_lambda0s = []

    for g in g_grid:
        def objective(lam: float) -> float:
            return -evaluate_ltt_log_likelihood(lam, g, trajectory)

        res = minimize_scalar(objective, bounds=(1e-4, 10.0), method="bounded")
        profile_lls.append(-res.fun)
        opt_lambda0s.append(res.x)

    profile_lls = np.array(profile_lls)
    best_idx = int(np.argmax(profile_lls))

    # Evaluate null model (G_l = 0)
    res_null = minimize_scalar(
        lambda lam: -evaluate_ltt_log_likelihood(lam, 0.0, trajectory),
        bounds=(1e-4, 10.0),
        method="bounded",
    )
    null_ll = -res_null.fun

    return ProfileLikelihoodSurface(
        g_l_grid=g_grid,
        profile_log_liks=profile_lls,
        best_g_l=float(g_grid[best_idx]),
        best_lambda0=float(opt_lambda0s[best_idx]),
        max_log_lik=float(profile_lls[best_idx]),
        null_log_lik=float(null_ll),
    )
