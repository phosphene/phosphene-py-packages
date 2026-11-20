"""L1 Analytical Unit & Dimensional Contract tests for holonomy.macroevo.

Verifies exact hand-calculated ground truths, dimensional invariants, and explicit
separation of domain precondition violations (ValueError) from exact model
falsification (-math.inf) across Units A–D and composite solvers.
"""

from __future__ import annotations

import math
import numpy as np
import pytest

from phosphene.holonomy.macroevo import (
    DiversityTrajectory,
    LineageObservation,
    MasterEquationParams,
    background_realization,
    binned_ltt_loglik,
    branching_loglik,
    carrying_capacity_profile,
    continuous_profile_likelihood_surface,
    equal_splits,
    joint_taphonomic_loglik,
    keiding_observability_prob,
    log_diversity_hazard,
    log_keiding_conditioning,
    log_lineage_duration_density,
    log_poisson_count_pmf,
    log_poisson_process_density,
    log_turnover_survival,
    master_equation_solution,
    newick_tip_paths,
    preservation_effort,
    profile_likelihood_surface,
    propagate_sparse_krylov,
    propagate_uniformized,
    standing_diversity_trajectory,
    tip_dr,
    tip_dr_diagnostic,
    tree_tip_dr_diagnostics,
)


# ============================================================================
# Unit A: Tip DR (Jetz et al. 2012) — Exact Tip-to-Root Hand Calculations
# ============================================================================

def test_tip_dr_exact_jetz_2012_formula_and_tip_to_root_ordering() -> None:
    # Tip-to-root path: terminal l_1 = 2.0, parent l_2 = 4.0, grandparent l_3 = 8.0
    # ES = 2.0 * 1 + 4.0 * 0.5 + 8.0 * 0.25 = 2 + 2 + 2 = 6.0; DR = 1 / 6.0
    path = (2.0, 4.0, 8.0)
    assert equal_splits(path, min_branch_length=1e-6) == pytest.approx(6.0, rel=1e-14)
    assert tip_dr(path, min_branch_length=1e-6) == pytest.approx(1.0 / 6.0, rel=1e-14)

    # Reversing the order (8.0, 4.0, 2.0) MUST give a different ES = 8 + 2 + 0.5 = 10.5
    assert equal_splits((8.0, 4.0, 2.0), min_branch_length=1e-6) == pytest.approx(10.5, rel=1e-14)


def test_newick_tip_paths_strictly_tip_to_root_and_singularity_detection() -> None:
    tree_str = "((TaxonA:0.0000001,TaxonB:1.5):2.0,TaxonC:3.5);"
    paths = newick_tip_paths(tree_str)

    # Tip-to-root: terminal branch first, parent internal branch second
    assert paths["TaxonA"] == pytest.approx((1e-7, 2.0))
    assert paths["TaxonB"] == pytest.approx((1.5, 2.0))
    assert paths["TaxonC"] == pytest.approx((3.5,))

    records = tree_tip_dr_diagnostics(paths, min_branch_length=1e-4, singularity_threshold=1e-6)
    rec_map = {r.taxon: r for r in records}

    assert rec_map["TaxonA"].has_singularity is True
    assert rec_map["TaxonB"].has_singularity is False
    assert rec_map["TaxonC"].has_singularity is False
    # TaxonB: ES = 1.5 + 2.0 * 0.5 = 2.5 -> DR = 0.4
    assert rec_map["TaxonB"].equal_splits == pytest.approx(2.5, rel=1e-14)
    assert rec_map["TaxonB"].diversification_rate == pytest.approx(0.4, rel=1e-14)


def test_tip_dr_domain_preconditions() -> None:
    with pytest.raises(ValueError):
        tip_dr([])
    with pytest.raises(ValueError):
        tip_dr([-0.1, 1.0])
    with pytest.raises(ValueError):
        tip_dr([1.0], min_branch_length=0.0)
    with pytest.raises(ValueError):
        tip_dr([math.nan])


# ============================================================================
# Unit B: Poisson Preservation — Count PMF vs. Point-Process Density
# ============================================================================

def test_poisson_exact_closed_forms_and_falsification_boundaries() -> None:
    # Discrete PMF: k=2, Theta=3.0 -> 2*ln(3) - 3 - ln(2)
    expected_pmf = 2.0 * math.log(3.0) - 3.0 - math.log(2.0)
    assert log_poisson_count_pmf(2, 3.0) == pytest.approx(expected_pmf, rel=1e-14)

    # Zero-effort boundaries: P(0|0) = 1 -> 0.0; P(k>0|0) = 0 -> -inf
    assert log_poisson_count_pmf(0, 0.0) == 0.0
    assert log_poisson_count_pmf(1, 0.0) == -math.inf

    # Continuous point-process density: k=2 occurrences in [1.0, 3.0], q=1.5
    # ln L = 2 * ln(1.5) - 1.5 * 2.0
    expected_pp = 2.0 * math.log(1.5) - 3.0
    assert log_poisson_process_density([2.5, 1.2], origin_age=3.0, extinction_age=1.0, preservation_rate=1.5) == pytest.approx(
        expected_pp, rel=1e-14
    )

    # Out-of-span occurrence is exact model falsification (-inf), not a crash
    assert log_poisson_process_density([3.5], origin_age=3.0, extinction_age=1.0, preservation_rate=1.5) == -math.inf

    # Invalid domains raise ValueError
    with pytest.raises(ValueError):
        log_poisson_count_pmf(-1, 1.0)
    with pytest.raises(ValueError):
        log_poisson_process_density([], origin_age=1.0, extinction_age=2.0, preservation_rate=1.0)


# ============================================================================
# Unit C: Keiding Conditioning — Small-Theta Taylor & Boundary Contracts
# ============================================================================

def test_keiding_small_theta_and_boundaries() -> None:
    assert keiding_observability_prob(0.0) == 0.0
    assert log_keiding_conditioning(0.0) == -math.inf

    theta = preservation_effort(duration=0.5, preservation_rate=2.0)
    assert theta == pytest.approx(1.0)
    assert keiding_observability_prob(theta) == pytest.approx(1.0 - math.exp(-1.0), rel=1e-14)
    assert log_keiding_conditioning(theta) == pytest.approx(math.log(1.0 - math.exp(-1.0)), rel=1e-14)

    # Tiny Theta = 1e-15 must not suffer 1 - exp(-Theta) == 0 catastrophic cancellation
    tiny = 1e-15
    assert log_keiding_conditioning(tiny) == pytest.approx(math.log(tiny) - 0.5 * tiny, rel=1e-14)

    with pytest.raises(ValueError):
        log_keiding_conditioning(-1e-3)


# ============================================================================
# Unit D: Lineage Duration & Turnover Survival
# ============================================================================

def test_lineage_duration_extinct_vs_extant_and_turnover_collapse() -> None:
    # Extinct: ln(0.5) - 0.5 * 2.0
    assert log_lineage_duration_density(2.0, 0.5, is_extant=False) == pytest.approx(
        math.log(0.5) - 1.0, rel=1e-14
    )
    # Extant (right-censored): -0.5 * 2.0
    assert log_lineage_duration_density(2.0, 0.5, is_extant=True) == pytest.approx(-1.0, rel=1e-14)
    # Zero extinction hazard boundaries
    assert log_lineage_duration_density(2.0, 0.0, is_extant=True) == 0.0
    assert log_lineage_duration_density(2.0, 0.0, is_extant=False) == -math.inf

    # Turnover collapses to pure extinction density when speciation_rate == 0
    assert log_turnover_survival(2.0, 0.0, 0.5, is_extant=False) == pytest.approx(
        log_lineage_duration_density(2.0, 0.5, is_extant=False), rel=1e-14
    )


# ============================================================================
# Composite Solvers: Unified Master Equation, Diversity Surface, Joint Likelihood
# ============================================================================

def test_unified_master_equation_and_propagator_equivalence() -> None:
    params = MasterEquationParams(lambda0=0.8, mu0=0.1, K=20.0, max_richness=15)
    times, probs = master_equation_solution(params, initial_richness=2, time_span=5.0, num_eval_points=10)
    assert not times.flags.writeable
    assert not probs.flags.writeable
    for col in range(10):
        np.testing.assert_allclose(np.sum(probs[:, col]), 1.0, atol=1e-4)

    brts = [3.0, 2.0, 1.0, 0.5]
    # S = 4 > K = 3 -> exact model falsification (-inf)
    assert branching_loglik(MasterEquationParams(lambda0=1.0, mu0=0.1, K=3.0), brts) == -math.inf

    # Padé, Krylov, and Jensen Uniformization agree on unified branching_loglik
    p_ok = MasterEquationParams(lambda0=0.9, mu0=0.15, K=15.0)
    ll_pade = branching_loglik(p_ok, brts)
    ll_krylov = branching_loglik(p_ok, brts, propagator=propagate_sparse_krylov)
    ll_unif = branching_loglik(p_ok, brts, propagator=propagate_uniformized)
    assert ll_pade == pytest.approx(ll_unif, rel=1e-10)
    assert ll_krylov == pytest.approx(ll_unif, rel=1e-10)

    # Kneebone background realization report is exported and consistent
    rep = background_realization(brts, lam0=0.9, mu0=0.15, K=15.0)
    assert math.isfinite(rep.rung0_loglik)
    assert math.isfinite(rep.rung3_loglik)
    assert rep.delta_loglik == pytest.approx(rep.rung3_loglik - rep.rung0_loglik)


def test_diversity_surface_binned_and_continuous() -> None:
    traj = DiversityTrajectory(
        time_bins_myr=np.array([4.0, 3.0, 2.0, 1.0, 0.0]),
        standing_diversity=np.array([2.0, 4.0, 6.0, 8.0]),
        speciation_events=np.array([1.0, 2.0, 1.0, 0.0]),
    )
    surf = profile_likelihood_surface(traj, g_l_min=-0.2, g_l_max=0.2, num_points=21)
    assert not surf.g_l_grid.flags.writeable
    assert surf.likelihood_ratio >= 0.0
    assert 0.0 <= surf.p_value <= 1.0
    assert surf.max_log_lik >= surf.null_log_lik

    # Continuous LTT surface
    t_grid = np.linspace(0.0, 5.0, 51)
    d_grid = np.full_like(t_grid, 4.0)
    c_surf = continuous_profile_likelihood_surface(
        speciation_times=[4.2, 3.1, 2.4, 1.5, 0.7],
        ltt_time_grid=t_grid,
        ltt_diversity_grid=d_grid,
        t_max_eval=5.0,
    )
    assert math.isfinite(c_surf.max_log_lik)
    assert c_surf.likelihood_ratio >= 0.0


def test_joint_taphonomic_loglik_breakdown() -> None:
    obs = [
        LineageObservation("t1", origin_age=3.0, extinction_age=1.8, occurrence_times=(2.8, 2.2, 1.9), preservation_rate=1.8, is_extant=False),
        LineageObservation("t2", origin_age=1.5, extinction_age=0.0, occurrence_times=(1.1, 0.4), preservation_rate=2.5, is_extant=True),
    ]
    res = joint_taphonomic_loglik(obs, extinction_rate=0.2, lambda0=0.4, g_l=-0.05)
    assert res.num_lineages == 2
    assert res.num_occurrences == 5
    assert res.total == pytest.approx(
        res.durations + res.speciation + res.occurrences - res.conditioning, rel=1e-14
    )
