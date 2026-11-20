"""L2 & L3 Hypothesis Property-Based Calibration Pyramid for Macroevolutionary Primitives.

Implements the codified patterns in docs/PYTEST_AND_HYPOTHESIS_PATTERNS.md:
- Pattern 1.1–1.5: Constructive manifolds, boundary-relative shrinkers, strict IEEE-754
  finite-domain hygiene, shrink-monotonic composites, and quantile coupling.
- Pattern 2.2: Vertex-seam continuity probes (+/- eps across regime transitions).
- Pattern 2.5: Profile likelihood dominance & zero-expectation score identities.
- Pattern 3.1–3.3: Variational defect hunting via ``target()``, regime stratification via
  ``event()``, and condition-scaled error budgets.
- Pattern 3.7: ``@example`` witness promotion on known stiff / near-singular corners.
"""

from __future__ import annotations

import math
import numpy as np
from hypothesis import event, example, given, strategies as st, target

from phosphene.holonomy.macroevo import (
    DiversityTrajectory,
    LineageObservation,
    binned_ltt_loglik,
    equal_splits,
    joint_taphonomic_loglik,
    keiding_observability_prob,
    log_keiding_conditioning,
    log_lineage_duration_density,
    log_poisson_count_pmf,
    log_poisson_process_density,
    profile_likelihood_surface,
    tip_dr,
)
from tests.strategies import (
    finite_floats,
    lineage_interval_and_occurrences,
    tip_to_root_branch_paths,
)


# ============================================================================
# Unit A: Tip DR Algebraic Properties & Regularization Seam Probes
# ============================================================================

@given(
    path=tip_to_root_branch_paths(min_edges=1, max_edges=10, min_len=0.0, max_len=20.0),
    scale=finite_floats(1e-3, 1e3),
    eps=finite_floats(1e-6, 1.0),
)
@example(path=(0.0, 1e-9, 2.0), scale=10.0, eps=1e-4)
def test_tip_dr_scale_equivariance_and_upper_bound(path, scale, eps):
    """DR(c * l, c * eps) == (1 / c) * DR(l, eps) and DR <= 1 / eps."""
    dr_base = tip_dr(path, min_branch_length=eps)
    scaled_path = tuple(l * scale for l in path)
    dr_scaled = tip_dr(scaled_path, min_branch_length=eps * scale)

    rel_defect = abs(dr_scaled * scale - dr_base) / max(dr_base, 1e-30)
    target(rel_defect, label="tip_dr_scale_equivariance_rel_defect")

    assert dr_base <= (1.0 / eps) * (1.0 + 1e-13)
    assert rel_defect <= 1e-12


@given(
    path=tip_to_root_branch_paths(min_edges=2, max_edges=8, min_len=0.0, max_len=10.0),
    delta=finite_floats(0.0, 5.0),
    eps=finite_floats(1e-5, 0.5),
)
def test_tip_dr_monotonic_non_increasing_in_branch_lengths(path, delta, eps):
    """Lengthening any branch cannot increase Tip DR."""
    bumped = (path[0] + delta,) + path[1:]
    assert tip_dr(bumped, min_branch_length=eps) <= tip_dr(path, min_branch_length=eps) + 1e-14


@given(
    eps=finite_floats(1e-5, 1.0),
    delta=finite_floats(1e-9, 1e-4),
    tail=tip_to_root_branch_paths(min_edges=0, max_edges=5, min_len=0.1, max_len=5.0),
)
def test_tip_dr_vertex_seam_continuity_across_regularization_floor(eps, delta, tail):
    """Pattern 2.2: Probe continuity across l_1 = eps - delta vs eps + delta."""
    l_below = max(0.0, eps - delta)
    l_above = eps + delta
    es_below = equal_splits((l_below,) + tail, min_branch_length=eps)
    es_above = equal_splits((l_above,) + tail, min_branch_length=eps)
    jump = abs(es_above - es_below)
    target(jump / delta, label="tip_dr_seam_lipschitz_ratio")
    assert jump <= delta * (1.0 + 1e-12) + 1e-15


# ============================================================================
# Unit B: Poisson Normalization, Interval Additivity & PMF/Density Bridge
# ============================================================================

@given(theta=finite_floats(0.05, 15.0))
def test_poisson_pmf_normalizes_to_unity(theta):
    """sum_{k=0}^{k_max} exp(log_poisson_count_pmf(k, theta)) == 1."""
    k_max = int(math.ceil(theta + 12.0 * math.sqrt(theta) + 30))
    total_prob = math.fsum(math.exp(log_poisson_count_pmf(k, theta)) for k in range(k_max + 1))
    defect = abs(total_prob - 1.0)
    target(defect, label="poisson_pmf_normalization_defect")
    assert defect <= 1e-12


@given(
    span=lineage_interval_and_occurrences(min_occ=0, max_occ=10),
    q=finite_floats(0.05, 10.0),
)
def test_poisson_process_density_exact_bridge_to_count_pmf(span, q):
    """Point-process density differs from count PMF by exactly -k*ln(dt) + ln(k!)."""
    s, e, occs = span
    dt = s - e
    k = len(occs)
    ll_pp = log_poisson_process_density(occs, origin_age=s, extinction_age=e, preservation_rate=q)
    ll_pmf = log_poisson_count_pmf(k, expected_count=q * dt)
    expected_diff = -k * math.log(dt) + math.lgamma(k + 1)
    defect = abs((ll_pp - ll_pmf) - expected_diff)
    target(defect, label="poisson_pp_pmf_bridge_defect")
    assert defect <= 1e-11 * max(1.0, abs(ll_pp))


# ============================================================================
# Unit C: Keiding Conditioning — Monotonicity, Concavity & Seam Continuity
# ============================================================================

@given(
    theta1=finite_floats(1e-14, 100.0),
    delta=finite_floats(1e-12, 10.0),
)
def test_keiding_monotonicity_and_bounds(theta1, delta):
    """Keiding probability in (0, 1] and log-conditioning in (-inf, 0], strictly increasing."""
    theta2 = theta1 + delta
    event(f"theta_decade={int(math.floor(math.log10(theta1)))}")
    p1 = keiding_observability_prob(theta1)
    p2 = keiding_observability_prob(theta2)
    lp1 = log_keiding_conditioning(theta1)
    lp2 = log_keiding_conditioning(theta2)

    assert 0.0 < p1 <= p2 <= 1.0
    assert lp1 <= lp2 <= 0.0


@given(delta=finite_floats(1e-16, 1e-13))
@example(delta=1e-15)
def test_keiding_vertex_seam_continuity_at_taylor_crossover(delta):
    """Pattern 2.2: Continuity across the Theta = 1e-12 Taylor crossover seam."""
    seam = 1e-12
    lp_below = log_keiding_conditioning(seam - delta)
    lp_above = log_keiding_conditioning(seam + delta)
    expected_diff = math.log(seam + delta) - math.log(seam - delta) - delta
    seam_defect = abs((lp_above - lp_below) - expected_diff)
    target(seam_defect, label="keiding_taylor_seam_defect")
    assert seam_defect <= 1e-13


# ============================================================================
# Unit D: Lineage Duration — Memorylessness & Score-Function Identity
# ============================================================================

@given(
    dt1=finite_floats(0.01, 20.0),
    dt2=finite_floats(0.01, 20.0),
    mu=finite_floats(0.01, 5.0),
)
def test_lineage_duration_extant_memorylessness(dt1, dt2, mu):
    """ln S(dt1 + dt2 | mu) == ln S(dt1 | mu) + ln S(dt2 | mu)."""
    lhs = log_lineage_duration_density(dt1 + dt2, mu, is_extant=True)
    rhs = (
        log_lineage_duration_density(dt1, mu, is_extant=True)
        + log_lineage_duration_density(dt2, mu, is_extant=True)
    )
    defect = abs(lhs - rhs)
    target(defect, label="duration_memorylessness_defect")
    assert defect <= 1e-12 * max(1.0, abs(lhs))


@given(
    mu=finite_floats(0.1, 5.0),
    quantiles=st.lists(finite_floats(0.02, 0.98), min_size=4, max_size=20),
)
def test_lineage_duration_quantile_coupled_mle_score_zero(mu, quantiles):
    """Pattern 1.5 & 2.5: At MLE mu_hat = N / sum(dt_i), finite-difference score vanishes."""
    # Push uniform quantiles through exact Exp(mu) inverse-CDF
    dts = [-math.log(1.0 - u) / mu for u in quantiles]
    mu_hat = len(dts) / math.fsum(dts)
    h = 1e-6 * mu_hat
    ll_plus = math.fsum(log_lineage_duration_density(dt, mu_hat + h, is_extant=False) for dt in dts)
    ll_minus = math.fsum(log_lineage_duration_density(dt, mu_hat - h, is_extant=False) for dt in dts)
    score = (ll_plus - ll_minus) / (2.0 * h)
    target(abs(score), label="duration_mle_score_residual")
    assert abs(score) <= 1e-5 * len(dts)


# ============================================================================
# Composite Calibration: Profile Likelihood Dominance (Pattern 2.5)
# ============================================================================

@given(
    d_vals=st.lists(finite_floats(1.0, 12.0), min_size=3, max_size=6),
    k_vals=st.lists(st.integers(min_value=1, max_value=5), min_size=3, max_size=6),
    test_lam0=finite_floats(0.05, 5.0),
)
def test_diversity_surface_profile_dominance_and_nesting(d_vals, k_vals, test_lam0):
    """Pattern 2.5: Profile MLE at G_l dominates any fixed lambda0, and full >= null."""
    m = min(len(d_vals), len(k_vals))
    bins = np.arange(m, -1, -1, dtype=np.float64)
    traj = DiversityTrajectory(
        time_bins_myr=bins,
        standing_diversity=np.array(d_vals[:m], dtype=np.float64),
        speciation_events=np.array(k_vals[:m], dtype=np.float64),
    )
    surf = profile_likelihood_surface(traj, g_l_min=-0.25, g_l_max=0.25, num_points=21)
    assert surf.max_log_lik >= surf.null_log_lik - 1e-12

    max_violation = 0.0
    for g_val, prof_ll in zip(surf.g_l_grid, surf.profile_log_liks):
        fixed_ll = binned_ltt_loglik(test_lam0, float(g_val), traj)
        max_violation = max(max_violation, max(0.0, fixed_ll - float(prof_ll)))
        assert fixed_ll <= float(prof_ll) + 1e-10
    target(max_violation, label="profile_dominance_violation")
