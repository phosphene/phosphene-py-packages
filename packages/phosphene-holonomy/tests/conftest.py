"""Shared pytest fixtures and Hypothesis calibration profiles for holonomy.

Implements Pattern 3.5 (Solver-Backend Parameterization) and Pattern 3.7
(Hypothesis Profiles for fast CI vs. deep nightly calibration).
"""

from __future__ import annotations

import os
from typing import Callable

import numpy as np
import pytest
from hypothesis import HealthCheck, settings

from phosphene.holonomy.macroevo.escalation import (
    propagate_dense_pade,
    propagate_sparse_krylov,
)

# Pattern 3.7: Register fast CI and deep calibration profiles
settings.register_profile(
    "ci",
    max_examples=80,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
)
settings.register_profile(
    "calibration",
    max_examples=2000,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
)
settings.load_profile(os.getenv("HYPOTHESIS_PROFILE", "ci"))


@pytest.fixture(scope="session", params=["dense_pade", "sparse_krylov"])
def fast_propagator(request) -> Callable[[np.ndarray, np.ndarray, float], np.ndarray]:
    """Parameterized Rung 2 semigroup backend fixture (Pattern 3.5)."""
    if request.param == "dense_pade":
        return propagate_dense_pade
    return propagate_sparse_krylov

