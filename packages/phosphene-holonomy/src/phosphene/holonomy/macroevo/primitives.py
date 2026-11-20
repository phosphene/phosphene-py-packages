"""Canonical pure-functional macroevolutionary primitives (Rung 0 & Rung 1).

Self-sufficient units of mathematical reason for birth-death diversification,
taphonomic observation conditioning, and phylogenetic tip rates:
- Unit A (Tip DR): Jetz et al. (2012) Equal Splits & Tip Diversification Rate (tip-to-root).
- Unit B (Poisson): Discrete count PMF and continuous point-process log-likelihood.
- Unit C (Keiding): Keiding (1975) / Foote (1997) preservation observability conditioning.
- Unit D (Lineage Duration): Exponential extinction density & birth-death turnover survival.
- Diversity Hazard & Standing Diversity: Exponential diversity-dependent hazard & D(t) step function.

Genealogy:
    Rung: 0 (stdlib ``math`` scalar closed forms) and 1 (read-only ``numpy`` 1D trajectories).
    Core Mapping: Pure Transform primitives with zero disk I/O, zero study prose, and
    strict separation between domain precondition errors (ValueError) and exact model
    falsification (-math.inf).
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Sequence

import numpy as np


def _require_finite(name: str, value: float) -> float:
    if not math.isfinite(value):
        raise ValueError(f"{name} must be finite, got {value}")
    return float(value)


# ============================================================================
# Unit A: Tip Diversification Rate (Jetz et al. 2012, Redding & Mooers 2006)
# ============================================================================

@dataclass(frozen=True)
class TipBranchPath:
    """Immutable tip-to-root branch length sequence for a single phylogenetic tip.

    Genealogy:
        Rung: 0 immutable value object.
        Literature: Redding & Mooers (2006) Syst. Biol. 55:644–654; Jetz et al. (2012) Nature 491:444–448.

    Dimensions:
        tip_to_root_lengths: Tuple of non-negative branch lengths [T], where index 0 is
            the terminal pendant branch and index -1 is the rootward edge.

    Boundary & Falsification Semantics:
        - Empty sequence, negative branch length, or non-finite value -> raises ValueError.
    """

    tip_to_root_lengths: tuple[float, ...]

    def __post_init__(self) -> None:
        if len(self.tip_to_root_lengths) == 0:
            raise ValueError("tip_to_root_lengths must contain at least one branch length")
        cleaned = tuple(_require_finite(f"branch[{i}]", float(l)) for i, l in enumerate(self.tip_to_root_lengths))
        for i, l in enumerate(cleaned):
            if l < 0.0:
                raise ValueError(f"Branch length at index {i} must be >= 0.0, got {l}")
        object.__setattr__(self, "tip_to_root_lengths", cleaned)


@dataclass(frozen=True)
class TipDRDiagnostic:
    """Self-sufficient diagnostic bundle for Jetz et al. (2012) Tip Diversification Rate.

    Dimensions:
        equal_splits: [T] Equal Splits evolutionary distinctiveness ES_i.
        diversification_rate: [T^-1] Tip Diversification Rate DR_i = 1 / ES_i.
        min_branch_length: [T] Minimum raw branch length along tip-to-root path.
        terminal_branch_length: [T] Terminal pendant branch length l_1.
        has_singularity: [bool] True if any edge is below ``singularity_threshold``.
    """

    equal_splits: float
    diversification_rate: float
    min_branch_length: float
    terminal_branch_length: float
    has_singularity: bool


def regularized_inverse_branch_length(
    length: float,
    min_branch_length: float = 1e-6,
) -> float:
    """Regularized reciprocal of a branch length guarding against polytomy singularities.

    Genealogy:
        Rung: 0 (Scalar closed-form; stdlib ``math`` only, zero arrays).
        Literature: Jetz et al. (2012) Nature 491:444–448.

    Objective:
        inv(l, eps) = 1 / max(l, eps)

    Dimensions:
        length (l): [T] Non-negative branch length (l >= 0).
        min_branch_length (eps): [T] Positive regularization floor (eps > 0).
        Returns: [T^-1] Regularized inverse branch length in (0, 1/eps].

    Boundary & Falsification Semantics:
        - l < 0, eps <= 0, or non-finite inputs -> raises ValueError.

    Invariants & Oracles:
        - Scale equivariance: inv(c * l, c * eps) == (1 / c) * inv(l, eps) for c > 0.
        - Bounded above by 1 / eps; monotonically non-increasing in l.
    """
    l_val = _require_finite("length", length)
    eps = _require_finite("min_branch_length", min_branch_length)
    if l_val < 0.0:
        raise ValueError(f"length must be >= 0.0, got {l_val}")
    if eps <= 0.0:
        raise ValueError(f"min_branch_length must be > 0.0, got {eps}")
    return 1.0 / max(l_val, eps)


def equal_splits(
    tip_to_root_lengths: Sequence[float],
    min_branch_length: float = 1e-6,
) -> float:
    """Equal Splits evolutionary distinctiveness (ES_i) along a tip-to-root branch path.

    Genealogy:
        Rung: 0 (Scalar closed-form reduction using ``math.fsum``; zero arrays).
        Literature: Redding & Mooers (2006) Syst. Biol. 55:644–654; Jetz et al. (2012) Nature 491:444–448.

    Objective:
        ES_i(eps) = sum_{j=1}^N max(l_j, eps) * 2^(-(j-1))
        where l_1 (index 0) is the terminal pendant branch and l_N is rootward.

    Dimensions:
        tip_to_root_lengths (l_j): [T] Sequence of non-negative branch lengths (len >= 1).
        min_branch_length (eps): [T] Positive per-edge regularization floor (eps > 0).
        Returns: [T] Equal Splits score ES_i >= eps.

    Boundary & Falsification Semantics:
        - Empty sequence, any l_j < 0, eps <= 0, or non-finite inputs -> raises ValueError.

    Invariants & Oracles:
        - Strictly positive: ES_i >= eps.
        - Scale equivariance: ES(c * l, c * eps) == c * ES(l, eps) for c > 0.
        - Monotonically non-decreasing in every branch length l_j.
    """
    eps = _require_finite("min_branch_length", min_branch_length)
    if eps <= 0.0:
        raise ValueError(f"min_branch_length must be > 0.0, got {eps}")
    path = TipBranchPath(tuple(tip_to_root_lengths))
    terms = [max(l_j, eps) * math.ldexp(1.0, -idx) for idx, l_j in enumerate(path.tip_to_root_lengths)]
    return math.fsum(terms)


def tip_dr(
    tip_to_root_lengths: Sequence[float],
    min_branch_length: float = 1e-6,
) -> float:
    """Jetz et al. (2012) Tip Diversification Rate (DR_i = 1 / ES_i) on tip-to-root edges.

    Genealogy:
        Rung: 0 (Scalar closed-form; reciprocal of ``equal_splits``).
        Literature: Jetz, Thomas, Joy, Hartmann, & Mooers (2012) Nature 491:444–448.

    Objective:
        DR_i(eps) = ( sum_{j=1}^N max(l_j, eps) * 2^(-(j-1)) )^(-1)
        where l_1 (index 0) is the terminal pendant branch and l_N is rootward.

    Dimensions:
        tip_to_root_lengths (l_j): [T] Tip-to-root branch lengths (len >= 1, l_j >= 0).
        min_branch_length (eps): [T] Positive per-edge regularization floor (eps > 0).
        Returns: [T^-1] Tip diversification rate in (0, 1 / eps].

    Boundary & Falsification Semantics:
        - Empty sequence, any l_j < 0, eps <= 0, or non-finite inputs -> raises ValueError.

    Invariants & Oracles:
        - Scale equivariance: DR(c * l, c * eps) == (1 / c) * DR(l, eps) for c > 0.
        - Monotonically non-increasing in every branch length l_j.
        - Upper bounded by 1 / eps; continuous across the regularization seam l_j = eps.
    """
    return 1.0 / equal_splits(tip_to_root_lengths, min_branch_length=min_branch_length)


def tip_dr_diagnostic(
    tip_to_root_lengths: Sequence[float],
    min_branch_length: float = 1e-4,
    singularity_threshold: float = 1e-6,
) -> TipDRDiagnostic:
    """Complete Jetz et al. (2012) Tip DR and polytomy singularity diagnostic bundle.

    Genealogy:
        Rung: 0 (Scalar diagnostic composition of ``equal_splits`` and ``tip_dr``).
        Literature: Jetz et al. (2012) Nature 491:444–448.

    Objective:
        ES_i = equal_splits(l, eps); DR_i = 1 / ES_i;
        has_singularity = (min_j l_j < singularity_threshold)

    Dimensions:
        tip_to_root_lengths: [T] Tip-to-root branch lengths (len >= 1, l_j >= 0).
        min_branch_length: [T] Positive regularization floor (> 0).
        singularity_threshold: [T] Threshold below which an edge is flagged as a polytomy artifact (> 0).
        Returns: TipDRDiagnostic bundle.

    Boundary & Falsification Semantics:
        - Invalid path or non-positive/non-finite thresholds -> raises ValueError.
    """
    thresh = _require_finite("singularity_threshold", singularity_threshold)
    if thresh <= 0.0:
        raise ValueError(f"singularity_threshold must be > 0.0, got {thresh}")
    path = TipBranchPath(tuple(tip_to_root_lengths))
    es = equal_splits(path.tip_to_root_lengths, min_branch_length=min_branch_length)
    min_l = min(path.tip_to_root_lengths)
    return TipDRDiagnostic(
        equal_splits=es,
        diversification_rate=1.0 / es,
        min_branch_length=min_l,
        terminal_branch_length=path.tip_to_root_lengths[0],
        has_singularity=(min_l < thresh),
    )


# Backward-compatibility alias
tip_diversification_rate = tip_dr


# ============================================================================
# Unit B: Poisson Preservation & Occurrence Process
# ============================================================================

def log_poisson_count_pmf(
    k: int,
    expected_count: float,
) -> float:
    """Log probability mass of observing k fossil occurrences under Poisson effort Theta.

    Genealogy:
        Rung: 0 (Scalar closed-form; stdlib ``math.log`` & ``math.lgamma``, zero arrays).
        Literature: Foote (1997) Paleobiology 23(2):181–206.

    Objective:
        ln P(K = k | Theta) = k * ln(Theta) - Theta - ln Gamma(k + 1)

    Dimensions:
        k: [count] Non-negative integer count of occurrences (k >= 0).
        expected_count (Theta): [dimensionless] Expected count q * Delta_t >= 0.
        Returns: [nats] Log probability mass in [-inf, 0.0].

    Boundary & Falsification Semantics:
        - k < 0, Theta < 0, or non-finite Theta -> raises ValueError.
        - k == 0 and Theta == 0.0 -> returns 0.0 (P(0 | 0) = 1).
        - k > 0 and Theta == 0.0 -> returns -math.inf (positive finds falsify zero effort).

    Invariants & Oracles:
        - Normalized PMF: sum_{k=0}^{inf} exp(ln P(k | Theta)) == 1.
        - Non-positive for all k >= 0, Theta >= 0.
    """
    if isinstance(k, bool) or not isinstance(k, int) or k < 0:
        raise ValueError(f"k must be a non-negative integer, got {k!r}")
    theta = _require_finite("expected_count", expected_count)
    if theta < 0.0:
        raise ValueError(f"expected_count must be >= 0.0, got {theta}")
    if theta == 0.0:
        return 0.0 if k == 0 else -math.inf
    return float(k * math.log(theta) - theta - math.lgamma(k + 1))


def log_poisson_process_density(
    occurrence_times: Sequence[float],
    origin_age: float,
    extinction_age: float,
    preservation_rate: float,
) -> float:
    """Log-likelihood density of exact occurrence timestamps under a homogeneous Poisson process.

    Genealogy:
        Rung: 0 (Scalar closed-form point-process density; stdlib ``math``, zero arrays).
        Literature: Silvestro et al. (2014) Syst. Biol. 63(3):349–367; Foote (1997).

    Objective:
        ln L({t_i}_{i=1}^k | s, e, q) = k * ln(q) - q * (s - e),   for all e <= t_i <= s

    Dimensions:
        occurrence_times (t_i): [T] Observed fossil occurrence ages before present.
        origin_age (s): [T] Lineage origination age (s >= e >= 0).
        extinction_age (e): [T] Lineage extinction age (e >= 0).
        preservation_rate (q): [occ * lineage^-1 * T^-1] Homogeneous preservation intensity (q >= 0).
        Returns: [nats] Point-process log-likelihood density.

    Boundary & Falsification Semantics:
        - s < e, e < 0, q < 0, or non-finite inputs -> raises ValueError.
        - Any t_i outside [e, s] -> returns -math.inf (exact model falsification: fossil outside lifespan).
        - k > 0 and q == 0.0 -> returns -math.inf (positive finds falsify zero preservation rate).
        - k == 0 -> returns -q * (s - e) (0.0 if q == 0 or s == e).

    Invariants & Oracles:
        - Additivity over disjoint time intervals partitioning [e, s].
        - Differs from ``log_poisson_count_pmf(k, q*(s-e))`` by exactly ``-k*ln(s-e) + ln(k!)``.
    """
    s = _require_finite("origin_age", origin_age)
    e = _require_finite("extinction_age", extinction_age)
    q = _require_finite("preservation_rate", preservation_rate)
    if e < 0.0 or s < e:
        raise ValueError(f"Requires origin_age >= extinction_age >= 0.0, got s={s}, e={e}")
    if q < 0.0:
        raise ValueError(f"preservation_rate must be >= 0.0, got {q}")

    duration = s - e
    k = len(occurrence_times)
    if k == 0:
        return float(-q * duration)

    for idx, t_raw in enumerate(occurrence_times):
        t = _require_finite(f"occurrence_times[{idx}]", float(t_raw))
        if t < e or t > s:
            return -math.inf

    if q == 0.0:
        return -math.inf

    return float(k * math.log(q) - q * duration)


# ============================================================================
# Unit C: Keiding (1975) / Foote (1997) Preservation Conditioning
# ============================================================================

def preservation_effort(
    duration: float,
    preservation_rate: float,
) -> float:
    """Dimensionless integrated preservation effort Theta = q * Delta_t.

    Genealogy:
        Rung: 0 (Scalar dimensional contraction).

    Objective:
        Theta = q * Delta_t

    Dimensions:
        duration (Delta_t): [T] Lineage duration >= 0.
        preservation_rate (q): [T^-1] Homogeneous preservation intensity >= 0.
        Returns: [dimensionless] Integrated preservation effort Theta >= 0.

    Boundary & Falsification Semantics:
        - duration < 0, preservation_rate < 0, or non-finite inputs -> raises ValueError.
    """
    dt = _require_finite("duration", duration)
    q = _require_finite("preservation_rate", preservation_rate)
    if dt < 0.0:
        raise ValueError(f"duration must be >= 0.0, got {dt}")
    if q < 0.0:
        raise ValueError(f"preservation_rate must be >= 0.0, got {q}")
    return float(q * dt)


def keiding_observability_prob(preservation_effort: float) -> float:
    """Probability that a lineage leaves at least one preserved fossil: P(K >= 1 | Theta).

    Genealogy:
        Rung: 0 (Scalar closed-form; stdlib ``math.expm1``, zero arrays).
        Literature: Keiding (1975) Ann. Stat. 3(2):363–372; Foote (1997) Paleobiology 23(2):181–206.

    Objective:
        P(K >= 1 | Theta) = 1 - exp(-Theta) = -expm1(-Theta)

    Dimensions:
        preservation_effort (Theta): [dimensionless] Integrated effort int_e^s q(t) dt >= 0.
        Returns: [probability] Value in [0.0, 1.0].

    Boundary & Falsification Semantics:
        - Theta < 0 or non-finite -> raises ValueError.
        - Theta == 0.0 -> returns 0.0.

    Invariants & Oracles:
        - Strictly increasing and concave on [0, inf); bounded in [0, 1].
        - Avoids catastrophic cancellation as Theta -> 0+ via ``-math.expm1(-Theta)``.
    """
    theta = _require_finite("preservation_effort", preservation_effort)
    if theta < 0.0:
        raise ValueError(f"preservation_effort must be >= 0.0, got {theta}")
    if theta == 0.0:
        return 0.0
    return float(-math.expm1(-theta))


def log_keiding_conditioning(preservation_effort: float) -> float:
    """Log probability that a lineage is observed at least once under Poisson sampling.

    Genealogy:
        Rung: 0 (Scalar closed-form; stdlib ``math`` only, zero arrays).
        Collapses From: Rung 1–3 taphonomic joint likelihoods conditioning on K >= 1.
        Literature: Keiding (1975) Ann. Stat. 3(2):363–372; Foote (1997) Paleobiology 23(2):181–206.

    Objective:
        ln P(K >= 1 | Theta) = ln(-expm1(-Theta))
        For 0 < Theta < 1e-12: ln(Theta) - Theta/2 + Theta^2/24 (small-Theta Taylor series).

    Dimensions:
        preservation_effort (Theta): [dimensionless] Integrated effort int_e^s q(t) dt >= 0.
        Returns: [nats] Log probability in [-inf, 0.0].

    Boundary & Falsification Semantics:
        - Theta < 0 or non-finite -> raises ValueError.
        - Theta == 0.0 -> returns -math.inf (zero preservation effort falsifies observation).

    Invariants & Oracles:
        - Strictly increasing and concave on (0, inf); bounded above by 0.0.
        - Vertex seam at Theta = 1e-12 continuous to < 1e-14 relative error.
    """
    theta = _require_finite("preservation_effort", preservation_effort)
    if theta < 0.0:
        raise ValueError(f"preservation_effort must be >= 0.0, got {theta}")
    if theta == 0.0:
        return -math.inf
    if theta < 1e-12:
        return float(math.log(theta) - 0.5 * theta + (theta * theta) / 24.0)
    prob = -math.expm1(-theta)
    return float(math.log(prob))


# ============================================================================
# Unit D: Lineage Duration & Survival Density
# ============================================================================

def log_lineage_duration_density(
    duration: float,
    extinction_rate: float,
    is_extant: bool = False,
) -> float:
    """Log waiting-time density (extinct) or survival probability (extant) under constant extinction.

    Genealogy:
        Rung: 0 (Scalar closed-form exponential waiting time; stdlib ``math``, zero arrays).
        Collapses From: Pure-death (lam0 = 0, k = 1) limit of Rung 2–3 master equations.
        Literature: Kendall (1948) Ann. Math. Stat. 19:1–15; Keiding (1975) Ann. Stat. 3(2):363–372.

    Objective:
        is_extant == False: ln f(Delta_t | mu) = ln(mu) - mu * Delta_t
        is_extant == True:  ln S(Delta_t | mu) = -mu * Delta_t

    Dimensions:
        duration (Delta_t): [T] Lineage duration s - e >= 0.
        extinction_rate (mu): [T^-1] Constant per-lineage extinction hazard >= 0.
        is_extant: [bool] True if lineage is right-censored at the present (e == 0, surviving).
        Returns: [nats] Log density (extinct) or log survival probability (extant).

    Boundary & Falsification Semantics:
        - duration < 0, extinction_rate < 0, or non-finite inputs -> raises ValueError.
        - extinction_rate == 0.0 and is_extant == True -> returns 0.0.
        - extinction_rate == 0.0 and is_extant == False -> returns -math.inf (zero hazard falsifies extinction).

    Invariants & Oracles:
        - Exact normalization: int_0^inf exp(ln f(t | mu)) dt == 1 for all mu > 0.
        - Memorylessness: ln S(t1 + t2 | mu) == ln S(t1 | mu) + ln S(t2 | mu).
    """
    dt = _require_finite("duration", duration)
    mu = _require_finite("extinction_rate", extinction_rate)
    if dt < 0.0:
        raise ValueError(f"duration must be >= 0.0, got {dt}")
    if mu < 0.0:
        raise ValueError(f"extinction_rate must be >= 0.0, got {mu}")

    survival_term = -mu * dt
    if is_extant:
        return float(survival_term)
    if mu == 0.0:
        return -math.inf
    return float(math.log(mu) + survival_term)


def log_turnover_survival(
    duration: float,
    speciation_rate: float,
    extinction_rate: float,
    is_extant: bool = False,
) -> float:
    """Log birth-death turnover survival (extant) or termination density (extinct) over a lineage span.

    Genealogy:
        Rung: 0 (Scalar closed-form; stdlib ``math`` only, zero arrays).
        Collapses To: ``log_lineage_duration_density`` when ``speciation_rate == 0.0``.
        Literature: Kendall (1948); Keiding (1975).

    Objective:
        is_extant == True:  -(lam + mu) * Delta_t
        is_extant == False: ln(mu) - (lam + mu) * Delta_t

    Dimensions:
        duration (Delta_t): [T] Lineage duration >= 0.
        speciation_rate (lam): [T^-1] Mean speciation hazard >= 0.
        extinction_rate (mu): [T^-1] Mean extinction hazard >= 0.
        Returns: [nats] Log turnover likelihood.

    Boundary & Falsification Semantics:
        - Negative or non-finite inputs -> raises ValueError.
        - mu == 0.0 and is_extant == False -> returns -math.inf.
    """
    dt = _require_finite("duration", duration)
    lam = _require_finite("speciation_rate", speciation_rate)
    mu = _require_finite("extinction_rate", extinction_rate)
    if dt < 0.0:
        raise ValueError(f"duration must be >= 0.0, got {dt}")
    if lam < 0.0:
        raise ValueError(f"speciation_rate must be >= 0.0, got {lam}")
    if mu < 0.0:
        raise ValueError(f"extinction_rate must be >= 0.0, got {mu}")

    survival_term = -(lam + mu) * dt
    if is_extant:
        return float(survival_term)
    if mu == 0.0:
        return -math.inf
    return float(math.log(mu) + survival_term)


# ============================================================================
# Diversity-Dependent Hazard & Standing Diversity Trajectory
# ============================================================================

def log_diversity_hazard(
    base_rate: float,
    g_coeff: float,
    diversity: float,
    clamp_bound: float = 50.0,
) -> float:
    """Numerically stable log-hazard under exponential diversity-dependence.

    Genealogy:
        Rung: 0 (Scalar closed-form; stdlib ``math`` only, zero arrays).
        Collapses To: Constant ``ln(base_rate)`` when ``g_coeff == 0.0`` or ``diversity == 0.0``.
        Literature: Silvestro et al. (2014, 2019) PyRate exponential diversity dependence.

    Objective:
        ln lambda(D) = clip(ln(lambda_0) + G_l * D, -clamp_bound, +clamp_bound)

    Dimensions:
        base_rate (lambda_0): [T^-1] Baseline per-lineage rate (> 0).
        g_coeff (G_l): [lineage^-1] Fractional hazard slope per co-occurring lineage.
        diversity (D): [lineages] Standing lineage richness (>= 0).
        clamp_bound: [nats] Finite symmetric clamp bound (> 0) preventing IEEE-754 overflow.
        Returns: [nats] Clamped log-hazard.

    Boundary & Falsification Semantics:
        - base_rate <= 0, diversity < 0, clamp_bound <= 0, or non-finite inputs -> raises ValueError.
    """
    lam0 = _require_finite("base_rate", base_rate)
    gl = _require_finite("g_coeff", g_coeff)
    div = _require_finite("diversity", diversity)
    bound = _require_finite("clamp_bound", clamp_bound)
    if lam0 <= 0.0:
        raise ValueError(f"base_rate must be > 0.0, got {lam0}")
    if div < 0.0:
        raise ValueError(f"diversity must be >= 0.0, got {div}")
    if bound <= 0.0:
        raise ValueError(f"clamp_bound must be > 0.0, got {bound}")

    raw_log = math.log(lam0) + gl * div
    return float(max(-bound, min(bound, raw_log)))


def diversity_hazard(
    base_rate: float,
    g_coeff: float,
    diversity: float,
    clamp_bound: float = 50.0,
) -> float:
    """Natural-scale exponential diversity-dependent hazard rate lambda(D) = lambda_0 * exp(G_l * D).

    Genealogy:
        Rung: 0 (Exponentiation of ``log_diversity_hazard``).

    Dimensions:
        Returns: [T^-1] Strictly positive hazard rate.
    """
    return math.exp(log_diversity_hazard(base_rate, g_coeff, diversity, clamp_bound=clamp_bound))


def standing_diversity_trajectory(
    lineage_intervals: Sequence[tuple[float, float]],
    eval_times: Sequence[float] | np.ndarray,
) -> np.ndarray:
    """Standing lineage richness step-function D(t) across arbitrary evaluation times.

    Genealogy:
        Rung: 1 (Read-only 1D ``numpy`` int64 trajectory).

    Objective:
        D(t) = sum_i I(e_i <= t <= s_i)

    Dimensions:
        lineage_intervals: Sequence of (origin_age s_i, extinction_age e_i) pairs [T] with s_i >= e_i.
        eval_times: Sequence of evaluation ages [T].
        Returns: Read-only 1D int64 array of standing diversity counts [lineages].

    Boundary & Falsification Semantics:
        - Any interval with s_i < e_i or non-finite endpoint -> raises ValueError.
        - Output array enforces ``flags.writeable == False``.
    """
    times = np.asarray(eval_times, dtype=np.float64)
    if not np.all(np.isfinite(times)):
        raise ValueError("eval_times must contain only finite values")

    counts = np.zeros(len(times), dtype=np.int64)
    for idx, (s_raw, e_raw) in enumerate(lineage_intervals):
        s = _require_finite(f"lineage_intervals[{idx}][0]", float(s_raw))
        e = _require_finite(f"lineage_intervals[{idx}][1]", float(e_raw))
        if s < e:
            raise ValueError(f"Lineage interval {idx} inverted: origin_age ({s}) < extinction_age ({e})")
        mask = (times <= s) & (times >= e)
        counts[mask] += 1

    counts.flags.writeable = False
    return counts


__all__ = [
    # Unit A: Tip DR
    "TipBranchPath",
    "TipDRDiagnostic",
    "regularized_inverse_branch_length",
    "equal_splits",
    "tip_dr",
    "tip_dr_diagnostic",
    "tip_diversification_rate",
    # Unit B: Poisson
    "log_poisson_count_pmf",
    "log_poisson_process_density",
    # Unit C: Keiding
    "preservation_effort",
    "keiding_observability_prob",
    "log_keiding_conditioning",
    # Unit D: Lineage Duration
    "log_lineage_duration_density",
    "log_turnover_survival",
    # Diversity Hazard & Standing Diversity
    "log_diversity_hazard",
    "diversity_hazard",
    "standing_diversity_trajectory",
]
