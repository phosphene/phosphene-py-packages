"""Constructive, shrink-monotonic Hypothesis strategies for holonomy calibration.

Enforces:
- Pattern 1.1: Constructive manifold generation (zero ``assume()`` on zero-measure sets).
- Pattern 1.2: Boundary-relative parameterization (``headroom = K - k``).
- Pattern 1.3: Strict IEEE-754 finite-domain hygiene (``allow_nan=False, allow_infinity=False, allow_subnormal=False``).
- Pattern 1.4: Shrink-monotonic composite generators (zero internal PRNG reseeding).
- Pattern 1.5: Common Random Numbers / uniform quantile strategies ``u in (0, 1)``.
"""

from __future__ import annotations

from typing import Tuple

import numpy as np
from hypothesis import strategies as st


def finite_floats(
    min_value: float,
    max_value: float,
    exclude_min: bool = False,
    exclude_max: bool = False,
) -> st.SearchStrategy[float]:
    """Strict IEEE-754 finite, normalized float strategy (Pattern 1.3)."""
    return st.floats(
        min_value=min_value,
        max_value=max_value,
        exclude_min=exclude_min,
        exclude_max=exclude_max,
        allow_nan=False,
        allow_infinity=False,
        allow_subnormal=False,
    )


@st.composite
def descending_branching_times(
    draw: st.DrawFn,
    min_splits: int = 2,
    max_splits: int = 6,
    min_dt: float = 0.05,
    max_dt: float = 2.0,
) -> Tuple[float, ...]:
    """Constructive strictly descending branching times t_1 > t_2 > ... > t_n > 0."""
    n_splits = draw(st.integers(min_value=min_splits, max_value=max_splits))
    deltas = draw(
        st.lists(
            finite_floats(min_dt, max_dt),
            min_size=n_splits,
            max_size=n_splits,
        )
    )
    return tuple(np.cumsum(deltas)[::-1].tolist())


@st.composite
def tip_to_root_branch_paths(
    draw: st.DrawFn,
    min_edges: int = 1,
    max_edges: int = 12,
    min_len: float = 0.0,
    max_len: float = 50.0,
) -> Tuple[float, ...]:
    """Constructive non-negative tip-to-root branch length sequences."""
    n = draw(st.integers(min_value=min_edges, max_value=max_edges))
    lengths = draw(
        st.lists(
            finite_floats(min_len, max_len),
            min_size=n,
            max_size=n,
        )
    )
    return tuple(lengths)


@st.composite
def lineage_interval_and_occurrences(
    draw: st.DrawFn,
    min_occ: int = 0,
    max_occ: int = 12,
) -> Tuple[float, float, Tuple[float, ...]]:
    """Constructive lineage span (s, e) with occurrence timestamps strictly inside [e, s].

    Uses quantile coupling u_i in [0, 1] mapped deterministically onto [e, s] (Pattern 1.5).
    """
    e = draw(finite_floats(0.0, 20.0))
    duration = draw(finite_floats(0.05, 15.0))
    s = e + duration
    k = draw(st.integers(min_value=min_occ, max_value=max_occ))
    quantiles = draw(st.lists(finite_floats(0.0, 1.0), min_size=k, max_size=k))
    occs = tuple(e + u * duration for u in sorted(quantiles, reverse=True))
    return s, e, occs

