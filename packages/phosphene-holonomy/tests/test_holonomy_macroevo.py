"""Unit tests for holonomy.macroevo replacements for PyRate."""

import numpy as np
import pytest

from phosphene.holonomy.macroevo import (
    DiversityTrajectory,
    FossilTaxonRecord,
    MasterEquationParams,
    compute_joint_taphonomic_likelihood,
    compute_profile_likelihood_surface,
    evaluate_ltt_log_likelihood,
    log_diversity_hazard,
    log_extinction_density,
    log_keiding_conditioning,
    log_poisson_occurrences,
    parse_simple_newick,
    audit_tree_diversification_rates,
    solve_master_equation,
    tip_diversification_rate,
)


def test_primitives_numerical_stability() -> None:
    # Kendall / Keiding conditioning
    ll_k = log_keiding_conditioning(lifespan=0.5, preservation_rate=2.0)
    assert isinstance(ll_k, float)
    assert ll_k < 0.0

    # Small dt limit should not underflow / divide by zero
    ll_k_small = log_keiding_conditioning(lifespan=1e-8, preservation_rate=1.0)
    assert np.isfinite(ll_k_small)

    # Poisson occurrences
    ll_p = log_poisson_occurrences(k_occurrences=3, lifespan=1.2, preservation_rate=1.5)
    assert isinstance(ll_p, float)

    # Clamped hazard
    haz = log_diversity_hazard(base_rate=0.2, g_coeff=0.05, diversity=10.0)
    assert isinstance(haz, float)


def test_diversity_surface_and_hypothesis_testing() -> None:
    # 5 time bins, 4 intervals
    bins = np.array([4.0, 3.0, 2.0, 1.0, 0.0])
    diversity = np.array([2.0, 4.0, 6.0, 8.0])
    speciation = np.array([1, 2, 1, 0])

    traj = DiversityTrajectory(
        time_bins_myr=bins,
        standing_diversity=diversity,
        speciation_events=speciation,
    )

    surface = compute_profile_likelihood_surface(traj, g_l_min=-0.2, g_l_max=0.2, num_points=11)

    assert len(surface.g_l_grid) == 11
    assert np.isfinite(surface.max_log_lik)
    assert np.isfinite(surface.null_log_lik)
    assert surface.likelihood_ratio >= 0.0
    assert 0.0 <= surface.p_value <= 1.0


def test_master_equation_continuous_solution() -> None:
    params = MasterEquationParams(lambda0=0.4, mu0=0.1, K=20.0, max_richness=15)
    times, probs = solve_master_equation(params, initial_richness=2, time_span=5.0, num_eval_points=10)

    assert len(times) == 10
    assert probs.shape == (16, 10)
    # Total probability must sum to ~1.0 at all evaluated times
    for col in range(10):
        np.testing.assert_allclose(np.sum(probs[:, col]), 1.0, atol=1e-4)


def test_tip_dr_and_singularity_detection() -> None:
    # Newick with one near-zero branch (polytomy machine-epsilon)
    tree_str = "((TaxonA:0.000001,TaxonB:1.5):2.0,TaxonC:3.5);"
    parsed = parse_simple_newick(tree_str)

    assert "TaxonA" in parsed
    assert "TaxonB" in parsed
    assert "TaxonC" in parsed

    audits = audit_tree_diversification_rates(parsed, epsilon_myr=0.01)
    audit_map = {a.taxon: a for a in audits}

    assert audit_map["TaxonA"].has_singularity is True
    assert audit_map["TaxonB"].has_singularity is False
    assert np.isfinite(audit_map["TaxonA"].harmonic_dr)


def test_joint_taphonomic_likelihood() -> None:
    records = [
        FossilTaxonRecord(taxon_id="t1", lifespan_myr=1.2, num_occurrences=4, mean_standing_diversity=3.0),
        FossilTaxonRecord(taxon_id="t2", lifespan_myr=0.8, num_occurrences=2, mean_standing_diversity=4.0),
    ]

    ll = compute_joint_taphonomic_likelihood(
        records=records,
        lambda0=0.3,
        g_l=0.02,
        mu0=0.15,
        q_preservation=1.8,
    )

    assert isinstance(ll, float)
    assert np.isfinite(ll)
