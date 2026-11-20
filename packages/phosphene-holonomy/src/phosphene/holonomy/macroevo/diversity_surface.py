"""Deterministic profile likelihood surfaces and LRT diagnostics for diversity dependence.

Replaces opaque trans-dimensional MCMC samplers with exact, closed-form analytical
profile optimization of baseline speciation lambda_0(G_l) and formal chi-square
likelihood-ratio tests against density-independence (G_l = 0).

Genealogy:
    Rung: 1 (Read-only 1D ``numpy`` quadrature & exact closed-form profile MLE).
    Collapses To: Constant-rate Poisson process MLE ``lambda_0 = N / int D(t) dt`` at G_l = 0.
    Literature: Silvestro et al. (2014, 2019); Etienne et al. (2012).
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Sequence

import numpy as np
from scipy.optimize import minimize_scalar
from scipy.stats import chi2

from phosphene.holonomy.macroevo.primitives import log_diversity_hazard


@dataclass(frozen=True)
class DiversityTrajectory:
    """Immutable binned lineages-through-time (LTT) curve across discrete intervals.

    Dimensions:
        time_bins_myr: [T] Bin boundary ages (len = M + 1).
        standing_diversity: [lineages] Standing richness D_i per bin (len = M).
        speciation_events: [count] Observed speciation counts k_i per bin (len = M).
    """

    time_bins_myr: np.ndarray
    standing_diversity: np.ndarray
    speciation_events: np.ndarray

    def __post_init__(self) -> None:
        tb = np.array(self.time_bins_myr, dtype=np.float64, copy=True)
        sd = np.array(self.standing_diversity, dtype=np.float64, copy=True)
        se = np.array(self.speciation_events, dtype=np.float64, copy=True)
        if len(tb) != len(sd) + 1:
            raise ValueError("time_bins_myr must have length len(standing_diversity) + 1")
        if len(se) != len(sd):
            raise ValueError("speciation_events must match length of standing_diversity")
        tb.flags.writeable = False
        sd.flags.writeable = False
        se.flags.writeable = False
        object.__setattr__(self, "time_bins_myr", tb)
        object.__setattr__(self, "standing_diversity", sd)
        object.__setattr__(self, "speciation_events", se)


@dataclass(frozen=True)
class ProfileLikelihoodSurface:
    """Exact deterministic profile log-likelihood surface over diversity-dependence slope G_l.

    Dimensions:
        g_l_grid: [lineage^-1] Read-only grid of evaluated G_l values.
        profile_log_liks: [nats] Read-only profile log-likelihoods ln L(G_l, lam0_hat(G_l)).
        best_g_l: [lineage^-1] Maximum likelihood estimate of G_l.
        best_lambda0: [T^-1] Profile MLE baseline speciation rate at best_g_l.
        null_lambda0: [T^-1] Null MLE baseline speciation rate at G_l = 0.
        max_log_lik, null_log_lik: [nats] Full and null log-likelihoods.
    """

    g_l_grid: np.ndarray
    profile_log_liks: np.ndarray
    best_g_l: float
    best_lambda0: float
    max_log_lik: float
    null_log_lik: float
    null_lambda0: float = 0.0

    def __post_init__(self) -> None:
        gg = np.array(self.g_l_grid, dtype=np.float64, copy=True)
        pl = np.array(self.profile_log_liks, dtype=np.float64, copy=True)
        gg.flags.writeable = False
        pl.flags.writeable = False
        object.__setattr__(self, "g_l_grid", gg)
        object.__setattr__(self, "profile_log_liks", pl)

    @property
    def likelihood_ratio(self) -> float:
        """Likelihood-ratio statistic Lambda = 2 * max(0, ln L_full - ln L_null)."""
        return 2.0 * max(0.0, self.max_log_lik - self.null_log_lik)

    @property
    def p_value(self) -> float:
        """Chi-square p-value with 1 degree of freedom."""
        return float(1.0 - chi2.cdf(self.likelihood_ratio, df=1))

    @property
    def aic_null(self) -> float:
        """AIC of the 1-parameter null model (G_l = 0)."""
        return 2.0 * 1.0 - 2.0 * self.null_log_lik

    @property
    def aic_full(self) -> float:
        """AIC of the 2-parameter full model (lambda_0, G_l)."""
        return 2.0 * 2.0 - 2.0 * self.max_log_lik

    @property
    def delta_aic(self) -> float:
        """AIC_null - AIC_full (positive favors full diversity-dependent model)."""
        return self.aic_null - self.aic_full

    def excludes_zero(self, alpha: float = 0.05) -> bool:
        """Return True if G_l = 0 is rejected at significance level alpha."""
        return self.p_value < alpha


def binned_ltt_loglik(
    lambda0: float,
    g_l: float,
    trajectory: DiversityTrajectory,
) -> float:
    """Exact inhomogeneous Poisson process log-likelihood over a binned LTT trajectory.

    Genealogy:
        Rung: 1 (Quadrature over ``log_diversity_hazard``).

    Objective:
        ln L = sum_i [ k_i * ln(lambda(D_i)) - lambda(D_i) * D_i * Delta_t_i ]

    Dimensions:
        lambda0: [T^-1] (> 0); g_l: [lineage^-1]; Returns: [nats].
    """
    if not math.isfinite(lambda0) or lambda0 <= 0.0:
        return -math.inf

    total_ll = 0.0
    dt_bins = np.abs(np.diff(trajectory.time_bins_myr))
    for k_i, d_i, dt_i in zip(trajectory.speciation_events, trajectory.standing_diversity, dt_bins):
        if d_i <= 0.0:
            continue
        ln_haz = log_diversity_hazard(lambda0, g_l, float(d_i))
        haz = math.exp(ln_haz)
        total_ll += float(k_i) * ln_haz - (haz * float(d_i) * float(dt_i))
    return float(total_ll)


def profile_likelihood_surface(
    trajectory: DiversityTrajectory,
    g_l_min: float = -0.5,
    g_l_max: float = 0.5,
    num_points: int = 101,
) -> ProfileLikelihoodSurface:
    """Deterministic profile likelihood surface over G_l for a binned LTT trajectory.

    Genealogy:
        Rung: 1 (Analytical closed-form profile MLE lambda_0_hat(G_l) = sum(k_i) / sum(D_i exp(G_l D_i) dt_i)).

    Objective:
        At each G_l, lambda_0_hat(G_l) = (sum k_i) / (sum D_i exp(G_l D_i) Delta_t_i)
        maximizes ln L(lambda_0, G_l) analytically with zero inner numerical optimizer error.

    Invariants & Oracles:
        - Profile dominance: ln L_profile(G_l) >= binned_ltt_loglik(lam0, G_l, trajectory) for all lam0 > 0.
        - Nesting: max_log_lik >= null_log_lik when 0.0 in [g_l_min, g_l_max].
    """
    dt_bins = np.abs(np.diff(trajectory.time_bins_myr))
    active = trajectory.standing_diversity > 0.0
    d_act = trajectory.standing_diversity[active]
    k_act = trajectory.speciation_events[active]
    dt_act = dt_bins[active]
    total_k = float(np.sum(k_act))

    def _analytic_profile(g: float) -> tuple[float, float]:
        gd = np.clip(g * d_act, -50.0, 50.0)
        denom = float(np.sum(d_act * np.exp(gd) * dt_act))
        if denom <= 0.0 or not math.isfinite(denom) or total_k <= 0.0:
            return -math.inf, 1e-6
        lam_hat = max(1e-8, total_k / denom)
        ll = binned_ltt_loglik(lam_hat, g, trajectory)
        return ll, lam_hat

    g_grid = np.linspace(g_l_min, g_l_max, num_points)
    lls = []
    lams = []
    for g in g_grid:
        ll, lam = _analytic_profile(float(g))
        lls.append(ll)
        lams.append(lam)

    ll_arr = np.array(lls, dtype=np.float64)
    best_idx = int(np.argmax(ll_arr))
    null_ll, null_lam = _analytic_profile(0.0)

    best_ll = float(ll_arr[best_idx])
    best_g = float(g_grid[best_idx])
    best_lam = float(lams[best_idx])
    if g_l_min <= 0.0 <= g_l_max and best_ll < null_ll:
        best_ll = null_ll
        best_g = 0.0
        best_lam = null_lam

    return ProfileLikelihoodSurface(
        g_l_grid=g_grid,
        profile_log_liks=ll_arr,
        best_g_l=best_g,
        best_lambda0=best_lam,
        max_log_lik=best_ll,
        null_log_lik=null_ll,
        null_lambda0=null_lam,
    )


def continuous_profile_likelihood_surface(
    speciation_times: Sequence[float],
    ltt_time_grid: Sequence[float] | np.ndarray,
    ltt_diversity_grid: Sequence[float] | np.ndarray,
    t_max_eval: float,
    is_per_lineage_process: bool = True,
    g_l_bounds: tuple[float, float] = (-10.0, 10.0),
    num_grid_points: int = 101,
) -> ProfileLikelihoodSurface:
    """Continuous-event profile likelihood over G_l with exact closed-form lambda_0_hat(G_l).

    Genealogy:
        Rung: 1 (Analytical closed-form profile MLE for lambda_0 + bounded 1D optimization over G_l).
        Literature: Silvestro et al. (2014) Syst. Biol.; Etienne et al. (2012).

    Objective:
        Lambda_clade(t) = D(t) * lambda_0 * exp(G_l * D(t))  [if is_per_lineage_process]
        ln L = sum_{i=1}^N ln Lambda_clade(ts_i) - int_0^{t_max} Lambda_clade(t) dt
        lambda_0_hat(G_l) = N / int_0^{t_max} scale(t) * exp(G_l * D(t)) dt

    Dimensions:
        speciation_times: [T] Observed speciation event ages (len >= 1).
        ltt_time_grid: [T] Monotonic or unsorted time grid.
        ltt_diversity_grid: [lineages] Standing diversity D(t) on grid.
        t_max_eval: [T] Upper integration bound (> 0).
        Returns: ``ProfileLikelihoodSurface`` with exact MLE, LRT, p-value, and AIC.

    Boundary & Falsification Semantics:
        - Empty speciation_times or t_max_eval <= 0 -> raises ValueError.
    """
    ts_arr = np.asarray(speciation_times, dtype=np.float64)
    n_sp = len(ts_arr)
    if n_sp == 0:
        raise ValueError("speciation_times must be non-empty")
    if not math.isfinite(t_max_eval) or t_max_eval <= 0.0:
        raise ValueError(f"t_max_eval must be finite and > 0.0, got {t_max_eval}")

    t_raw = np.asarray(ltt_time_grid, dtype=np.float64)
    d_raw = np.asarray(ltt_diversity_grid, dtype=np.float64)
    order = np.argsort(t_raw)
    t_grid = t_raw[order]
    d_grid = d_raw[order]

    def _div_at_t(t: float) -> float:
        idx = int(np.searchsorted(t_grid, t))
        if idx >= len(d_grid):
            idx = len(d_grid) - 1
        return float(d_grid[idx])

    d_at_events = np.array([_div_at_t(float(t)) for t in ts_arr], dtype=np.float64)

    mask = t_grid[:-1] <= t_max_eval
    dt = np.diff(t_grid)[mask]
    d_eval = d_grid[:-1][mask]

    scale_events = (
        np.log(np.maximum(1.0, d_at_events))
        if is_per_lineage_process
        else np.zeros_like(d_at_events)
    )
    scale_grid = d_eval if is_per_lineage_process else np.ones_like(d_eval)

    def _profile_gl(gl: float) -> tuple[float, float]:
        g_d_events = np.clip(gl * d_at_events, -50.0, 50.0)
        g_d_grid = np.clip(gl * d_eval, -50.0, 50.0)
        integral_factor = float(np.sum(scale_grid * np.exp(g_d_grid) * dt))
        if integral_factor <= 0.0 or not math.isfinite(integral_factor):
            return -1e12, 1e-6
        l0 = max(1e-6, n_sp / integral_factor)
        ll = float(np.sum(np.log(l0) + scale_events + g_d_events) - l0 * integral_factor)
        return ll, l0

    ll_null, l0_null = _profile_gl(0.0)
    opt_res = minimize_scalar(
        lambda gl: -_profile_gl(float(gl))[0],
        bounds=g_l_bounds,
        method="bounded",
    )
    mle_gl = float(opt_res.x)
    ll_full, l0_full = _profile_gl(mle_gl)
    if ll_full < ll_null:
        ll_full, l0_full, mle_gl = ll_null, l0_null, 0.0

    g_grid = np.linspace(g_l_bounds[0], g_l_bounds[1], num_grid_points)
    prof_lls = np.array([_profile_gl(float(g))[0] for g in g_grid], dtype=np.float64)

    return ProfileLikelihoodSurface(
        g_l_grid=g_grid,
        profile_log_liks=prof_lls,
        best_g_l=mle_gl,
        best_lambda0=l0_full,
        max_log_lik=ll_full,
        null_log_lik=ll_null,
        null_lambda0=l0_null,
    )


# Backward-compatibility aliases
evaluate_ltt_log_likelihood = binned_ltt_loglik
compute_profile_likelihood_surface = profile_likelihood_surface

__all__ = [
    "DiversityTrajectory",
    "ProfileLikelihoodSurface",
    "binned_ltt_loglik",
    "profile_likelihood_surface",
    "continuous_profile_likelihood_surface",
    "evaluate_ltt_log_likelihood",
    "compute_profile_likelihood_surface",
]
