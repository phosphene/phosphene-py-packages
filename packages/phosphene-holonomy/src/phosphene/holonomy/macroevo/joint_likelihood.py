"""Composite taphonomically conditioned diversification likelihood engine.

Integrates the four canonical Rung 0 primitives (Lineage Duration, Poisson Occurrences,
Keiding Conditioning, and Exponential Diversity Hazard) behind an abstract, domain-agnostic
``LineageObservation`` interface. Basin-to-rate mappings remain strictly in consumers.

Genealogy:
    Rung: 0/1 exact additive composition of canonical primitives.
    Literature: Kendall (1948); Keiding (1975); Foote (1997); Silvestro et al. (2014).
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Protocol, Sequence, runtime_checkable

import numpy as np

from phosphene.holonomy.macroevo.primitives import (
    log_diversity_hazard,
    log_keiding_conditioning,
    log_lineage_duration_density,
    log_poisson_process_density,
    preservation_effort,
    standing_diversity_trajectory,
)


@runtime_checkable
class LineageObservationProtocol(Protocol):
    """Structural protocol for any consumer lineage record entering joint likelihood evaluation."""

    @property
    def lineage_id(self) -> str: ...
    @property
    def origin_age(self) -> float: ...
    @property
    def extinction_age(self) -> float: ...
    @property
    def occurrence_times(self) -> Sequence[float]: ...
    @property
    def preservation_rate(self) -> float: ...
    @property
    def is_extant(self) -> bool: ...


@dataclass(frozen=True)
class LineageObservation:
    """Immutable, domain-agnostic fossil lineage observation record.

    Dimensions:
        origin_age (s): [T] Origination age before present (s >= e >= 0).
        extinction_age (e): [T] Extinction age before present (>= 0).
        occurrence_times: [T] Observed fossil occurrence ages within [e, s].
        preservation_rate (q): [occ * lineage^-1 * T^-1] Resolved lineage/basin intensity (> 0).
        is_extant: [bool] True if lineage survives to present (right-censored).
    """

    lineage_id: str
    origin_age: float
    extinction_age: float
    occurrence_times: tuple[float, ...]
    preservation_rate: float
    is_extant: bool = False

    def __post_init__(self) -> None:
        if self.extinction_age < 0.0 or self.origin_age < self.extinction_age:
            raise ValueError(
                f"Lineage {self.lineage_id}: requires origin_age >= extinction_age >= 0, "
                f"got s={self.origin_age}, e={self.extinction_age}"
            )
        if not math.isfinite(self.preservation_rate) or self.preservation_rate <= 0.0:
            raise ValueError(
                f"Lineage {self.lineage_id}: preservation_rate must be finite and > 0, got {self.preservation_rate}"
            )
        object.__setattr__(self, "occurrence_times", tuple(float(t) for t in self.occurrence_times))


@dataclass(frozen=True)
class JointLikelihoodBreakdown:
    """Full additive decomposition of the joint taphonomically conditioned log-likelihood.

    Objective:
        total = durations + speciation + occurrences - conditioning
    """

    total: float
    durations: float
    speciation: float
    occurrences: float
    conditioning: float
    num_lineages: int
    num_occurrences: int


def joint_taphonomic_loglik(
    observations: Sequence[LineageObservationProtocol],
    extinction_rate: float,
    lambda0: float | None = None,
    g_l: float = 0.0,
) -> JointLikelihoodBreakdown:
    """Exact joint taphonomically conditioned log-likelihood over lineage observations.

    Genealogy:
        Rung: 0/1 composite sum of ``log_lineage_duration_density``, ``log_poisson_process_density``,
            ``log_keiding_conditioning``, and optional ``log_diversity_hazard``.
        Collapses To: Pure duration + Poisson - Keiding likelihood when ``lambda0 is None``.

    Objective:
        ln L = sum_i [ ln f(s_i - e_i | mu, extant_i)
                     + ln L_occ(T_i | s_i, e_i, q_i)
                     - ln P(K >= 1 | q_i * (s_i - e_i))
                     + I(lambda0) * ln lambda(D(s_i)) ]

    Dimensions:
        extinction_rate (mu): [T^-1] (> 0).
        lambda0: Optional [T^-1] (> 0) baseline speciation rate.
        g_l: [lineage^-1] diversity-dependence slope.
        Returns: ``JointLikelihoodBreakdown`` in [nats].

    Boundary & Falsification Semantics:
        - extinction_rate <= 0 or non-finite -> raises ValueError.
        - Any occurrence outside [e_i, s_i] or zero-duration conditioning yields ``-math.inf``
          in the corresponding component (exact model falsification).
    """
    if not math.isfinite(extinction_rate) or extinction_rate <= 0.0:
        raise ValueError(f"extinction_rate must be finite and > 0.0, got {extinction_rate}")

    div_at_origins: np.ndarray | None = None
    if lambda0 is not None:
        intervals = [(obs.origin_age, obs.extinction_age) for obs in observations]
        origins = np.array([obs.origin_age for obs in observations], dtype=np.float64)
        div_at_origins = standing_diversity_trajectory(intervals, origins)

    total_dur = 0.0
    total_spec = 0.0
    total_occ = 0.0
    total_cond = 0.0
    total_occ_count = 0

    for idx, obs in enumerate(observations):
        s = float(obs.origin_age)
        e = float(obs.extinction_age)
        q = float(obs.preservation_rate)
        dt = s - e

        total_dur += log_lineage_duration_density(
            duration=dt,
            extinction_rate=extinction_rate,
            is_extant=obs.is_extant,
        )

        if lambda0 is not None and div_at_origins is not None:
            total_spec += log_diversity_hazard(
                base_rate=lambda0,
                g_coeff=g_l,
                diversity=float(div_at_origins[idx]),
            )

        total_occ += log_poisson_process_density(
            occurrence_times=obs.occurrence_times,
            origin_age=s,
            extinction_age=e,
            preservation_rate=q,
        )
        total_occ_count += len(obs.occurrence_times)

        effort = preservation_effort(duration=dt, preservation_rate=q)
        total_cond += log_keiding_conditioning(preservation_effort=effort)

    total = total_dur + total_spec + total_occ - total_cond
    return JointLikelihoodBreakdown(
        total=float(total),
        durations=float(total_dur),
        speciation=float(total_spec),
        occurrences=float(total_occ),
        conditioning=float(total_cond),
        num_lineages=len(observations),
        num_occurrences=total_occ_count,
    )


__all__ = [
    "LineageObservationProtocol",
    "LineageObservation",
    "JointLikelihoodBreakdown",
    "joint_taphonomic_loglik",
]
