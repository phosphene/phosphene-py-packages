"""Comparative evaluation tests: Galápagos avifauna vs. Hominin lineages in phosphene-holonomy."""

from __future__ import annotations

import numpy as np
import pytest

from phosphene.holonomy.macroevo import (
    MasterEquationParams,
    compute_etienne_branching_loglik,
    profile_etienne_k,
)

HOMO_BRANCHING_TIMES_MA: list[float] = [2.80, 2.31, 1.89, 1.21, 0.78, 0.43, 0.24]


def test_hominin_carrying_capacity_is_non_identifiable():
    """Verify that varying K across hominin lineages yields Delta lnL < 0.60 (flat profile)."""
    k_grid = [8.0, 10.0, 12.0, 15.0, 20.0, 30.0, 50.0, 100.0, 500.0]
    ks, lls = profile_etienne_k(
        HOMO_BRANCHING_TIMES_MA,
        k_grid=k_grid,
        fixed_lambda0=1.0,
        fixed_mu0=0.1,
        soc=2,
    )

    assert len(ks) == len(k_grid)
    assert np.all(np.isfinite(lls))

    delta_max = float(np.max(lls) - np.min(lls))
    assert delta_max < 0.60, f"Expected flat profile (delta < 0.60), got delta = {delta_max}"

    idx_15 = k_grid.index(15.0)
    idx_500 = k_grid.index(500.0)
    diff_15_500 = abs(lls[idx_15] - lls[idx_500])
    assert diff_15_500 < 0.40
