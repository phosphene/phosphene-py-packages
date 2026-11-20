"""Unit tests for the morphometrics dialect (skeletal landmarks and allometric growth)."""

import numpy as np
import pytest

from phosphene.holonomy.core import ControlLoop
from phosphene.holonomy.morphometrics import (
    Configuration,
    allometric_growth_closure,
    ontogenetic_trace,
    morphological_defect,
)


@pytest.fixture
def cranium_landmarks() -> np.ndarray:
    # 8 synthetic 3D cranial landmarks: glabella, inion, bregma, nasion, etc.
    return np.array([
        [0.0, 0.0, 10.0],
        [15.0, 0.0, 2.0],
        [-10.0, 0.0, 3.0],
        [0.0, 8.0, 5.0],
        [0.0, -8.0, 5.0],
        [8.0, 6.0, 0.0],
        [8.0, -6.0, 0.0],
        [-5.0, 0.0, -4.0],
    ], dtype=np.float64)


def test_configuration_immutability_and_centroid_size(cranium_landmarks):
    config = Configuration.from_landmarks(cranium_landmarks)
    assert not config.landmarks.flags.writeable
    assert config.centroid_size > 0.0

    with pytest.raises(ValueError):
        config.landmarks[0, 0] = 999.0


def test_ontogenetic_trace_and_morphological_defect(cranium_landmarks):
    config = Configuration.from_landmarks(cranium_landmarks)
    # Seasonal or masticatory cyclic loading schedule
    loading = ControlLoop.sinusoidal(period=10.0, num_steps=5, shape=cranium_landmarks.shape, amplitude=0.2)
    # Differential cranial growth coefficients
    coeffs = np.full(cranium_landmarks.shape, 0.05, dtype=np.float64)
    growth_closure = allometric_growth_closure(coeffs)

    trace = ontogenetic_trace(config, loading, growth_closure)
    assert len(trace) == 6

    defect = morphological_defect(trace)
    assert defect.norm > 0.0
    assert not defect.delta_values.flags.writeable
    assert defect.final_state.values.shape == cranium_landmarks.shape
