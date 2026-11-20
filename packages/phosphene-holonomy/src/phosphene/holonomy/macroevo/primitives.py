"""Pure functional mathematical primitives for macroevolutionary birth-death and taphonomic observation.

Decomposed from first principles to replace empirical MCMC drift with deterministic likelihoods:
- Kendall (1948): Continuous-time Markov birth-death process
- Keiding (1975): Survival conditioning for observable lineages
- Foote (1997): Continuous preservation and sampling probabilities
- Silvestro et al. (2014, 2019): Diversity-dependent hazard functions
- Jetz et al. (2012): Tip diversification rate (DR) metric

All primitives are numerically stable, operating in log-space where appropriate,
using expm1/log1p to prevent catastrophic floating-point cancellation.
"""

from __future__ import annotations

import math
from typing import Sequence

import numpy as np


def log_diversity_hazard(
    base_rate: float,
    g_coeff: float,
    diversity: float,
    clamp_bound: float = 50.0,
) -> float:
    """Primitive 1: Numerically stable log-hazard under exponential diversity-dependence.

    Formula:
        lambda(D) = lambda_0 * exp(G_l * D)
        ln lambda(D) = ln(lambda_0) + G_l * D

    Invariants:
        1. base_rate must be strictly positive.
        2. diversity must be non-negative.
        3. Returns finite log-hazard clamped within [-clamp_bound, +clamp_bound]
           to prevent IEEE 754 overflow/underflow.
    """
    if base_rate <= 0.0:
        raise ValueError(f"base_rate must be > 0.0, got {base_rate}")
    if diversity < 0.0:
        raise ValueError(f"diversity must be >= 0.0, got {diversity}")

    raw_log = math.log(base_rate) + g_coeff * diversity
    return float(np.clip(raw_log, -clamp_bound, clamp_bound))


def log_keiding_conditioning(
    lifespan: float,
    preservation_rate: float,
) -> float:
    """Primitive 2: Log probability that a lineage is observed at least once given lifespan.

    Formula (Keiding 1975, Foote 1997):
        P(observable | Delta t) = 1 - exp(-q * Delta t)
        ln P = log( -expm1(-q * Delta t) )

    Invariants:
        1. lifespan must be positive.
        2. preservation_rate must be positive.
        3. Uses -expm1(-q*dt) to prevent cancellation at small (q * dt).
    """
    if lifespan <= 0.0:
        raise ValueError(f"lifespan must be > 0.0, got {lifespan}")
    if preservation_rate <= 0.0:
        raise ValueError(f"preservation_rate must be > 0.0, got {preservation_rate}")

    z = preservation_rate * lifespan
    if z < 1e-15:
        return math.log(z)
    prob = -math.expm1(-z)
    prob = min(max(prob, 1e-300), 1.0)
    return math.log(prob)


def log_poisson_occurrences(
    k_occurrences: int,
    lifespan: float,
    preservation_rate: float,
) -> float:
    """Primitive 3: Log-likelihood of k fossil occurrences given lifespan.

    Formula:
        ln P(k | Delta t, q) = k * ln(q * Delta t) - (q * Delta t) - ln(k!)
    """
    if k_occurrences < 0:
        raise ValueError(f"k_occurrences must be non-negative, got {k_occurrences}")
    if lifespan <= 0.0:
        raise ValueError(f"lifespan must be > 0.0, got {lifespan}")
    if preservation_rate <= 0.0:
        raise ValueError(f"preservation_rate must be > 0.0, got {preservation_rate}")

    expected = preservation_rate * lifespan
    return float(k_occurrences * math.log(expected) - expected - math.lgamma(k_occurrences + 1))


def log_extinction_density(
    lifespan: float,
    mu_rate: float,
) -> float:
    """Primitive 4: Log probability density of lineage duration under constant extinction.

    Formula:
        ln f(Delta t | mu) = ln(mu) - mu * Delta t
    """
    if lifespan <= 0.0:
        raise ValueError(f"lifespan must be > 0.0, got {lifespan}")
    if mu_rate <= 0.0:
        raise ValueError(f"mu_rate must be > 0.0, got {mu_rate}")

    return float(math.log(mu_rate) - mu_rate * lifespan)


def regularized_inverse_branch_length(
    length_myr: float,
    epsilon_myr: float = 0.01,
) -> float:
    """Primitive 5: Regularized inverse branch length avoiding zero-length singularities.

    Formula:
        inv_len = 1.0 / max(length_myr, epsilon_myr)
    """
    if epsilon_myr <= 0.0:
        raise ValueError(f"epsilon_myr must be > 0.0, got {epsilon_myr}")

    effective_len = max(length_myr, epsilon_myr)
    return 1.0 / effective_len


def tip_diversification_rate(
    root_to_tip_branch_lengths: Sequence[float],
    epsilon_myr: float = 0.01,
) -> float:
    """Primitive 6: Jetz et al. (2012) Tip Diversification Rate (DR).

    Formula:
        DR_i = sum_{j=1}^{N_i} (l_j * (1/2)^(j-1))^(-1)
    """
    if len(root_to_tip_branch_lengths) == 0:
        raise ValueError("Must provide at least one branch length")

    weighted_len = 0.0
    for j, l_j in enumerate(root_to_tip_branch_lengths, start=1):
        weight = 0.5 ** (j - 1)
        weighted_len += l_j * weight

    return regularized_inverse_branch_length(weighted_len, epsilon_myr=epsilon_myr)
