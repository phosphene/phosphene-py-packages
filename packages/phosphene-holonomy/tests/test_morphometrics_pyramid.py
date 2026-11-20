"""L1–L3 Pytest & Hypothesis Calibration Pyramid for holonomy.morphometrics.

Verifies Kendall shape-space Procrustes invariances (translation, positive scale, SO(m)
proper rotation via skew-symmetric Lie algebra construction — Pattern 1.1), OLS allometric
residual orthogonality, and Foote (1993) weighted disparity equivariances with ``target()``
variational defect hunting.
"""

from __future__ import annotations

import math
import numpy as np
import pytest
from hypothesis import given, strategies as st, target
from scipy.linalg import expm

from phosphene.holonomy.morphometrics import (
    Configuration,
    allometric_residuals,
    generalized_procrustes,
    inverse_variance_weights,
    preshape,
    procrustes_alignment,
    weighted_morphological_disparity,
)
from tests.strategies import finite_floats


@st.composite
def nondegenerate_landmarks(draw: st.DrawFn, k: int = 5, m: int = 3) -> np.ndarray:
    """Constructive non-degenerate (k, m) landmark matrix with guaranteed centroid size > 0.5."""
    raw = np.array(
        draw(st.lists(finite_floats(-10.0, 10.0), min_size=k * m, max_size=k * m)),
        dtype=np.float64,
    ).reshape((k, m))
    # Add deterministic non-collinear simplex basis offset so centroid size is strictly bounded away from 0
    raw[0, 0] += 5.0
    raw[1, 1] += 5.0
    if m >= 3:
        raw[2, 2] += 5.0
    return raw


@st.composite
def so3_rotation(draw: st.DrawFn) -> np.ndarray:
    """Pattern 1.1: Constructive SO(3) rotation via expm of skew-symmetric Lie algebra so(3)."""
    a = draw(finite_floats(-math.pi, math.pi))
    b = draw(finite_floats(-math.pi, math.pi))
    c = draw(finite_floats(-math.pi, math.pi))
    skew = np.array(
        [[0.0, -c, b], [c, 0.0, -a], [-b, a, 0.0]],
        dtype=np.float64,
    )
    return expm(skew)


# ============================================================================
# Procrustes & Kendall Shape-Space Invariances
# ============================================================================

@given(
    pts=nondegenerate_landmarks(k=5, m=3),
    translation=st.lists(finite_floats(-50.0, 50.0), min_size=3, max_size=3),
    scale=finite_floats(0.05, 50.0),
    rot=so3_rotation(),
)
def test_procrustes_similarity_invariance_on_so3(pts, translation, scale, rot):
    """Procrustes distance vanishes under arbitrary translation, positive scaling, and SO(3) rotation."""
    cfg_a = Configuration.from_landmarks(pts)
    transformed = scale * (pts @ rot) + np.array(translation, dtype=np.float64)
    cfg_b = Configuration.from_landmarks(transformed)

    aln = procrustes_alignment(cfg_b, cfg_a, allow_reflection=False)
    assert not aln.aligned_landmarks.flags.writeable
    assert not aln.rotation_matrix.flags.writeable

    ortho_err = float(np.linalg.norm(aln.rotation_matrix.T @ aln.rotation_matrix - np.eye(3)))
    det_err = abs(float(np.linalg.det(aln.rotation_matrix)) - 1.0)
    target(aln.procrustes_distance, label="procrustes_so3_invariance_defect")

    assert ortho_err <= 1e-12
    assert det_err <= 1e-12
    assert aln.procrustes_distance <= 1e-11
    assert aln.riemannian_distance <= 1e-7


@given(pts_a=nondegenerate_landmarks(k=5, m=3), pts_b=nondegenerate_landmarks(k=5, m=3))
def test_procrustes_symmetry_and_gpa_convergence(pts_a, pts_b):
    """d_P(A, B) == d_P(B, A) and GPA converges onto a unit-norm consensus shape."""
    cfg_a = Configuration.from_landmarks(pts_a)
    cfg_b = Configuration.from_landmarks(pts_b)

    ab = procrustes_alignment(cfg_a, cfg_b)
    ba = procrustes_alignment(cfg_b, cfg_a)
    sym_defect = abs(ab.procrustes_distance - ba.procrustes_distance)
    target(sym_defect, label="procrustes_symmetry_defect")
    assert sym_defect <= 1e-11

    gpa = generalized_procrustes([cfg_a, cfg_b])
    assert gpa.converged is True
    assert not gpa.mean_shape.flags.writeable
    assert float(np.linalg.norm(gpa.mean_shape)) == pytest.approx(1.0, rel=1e-12)


# ============================================================================
# Allometric Residualization Invariants
# ============================================================================

@given(
    n=st.integers(min_value=4, max_value=12),
    slope=finite_floats(-2.0, 2.0),
    intercept=finite_floats(-3.0, 3.0),
    x_deltas=st.lists(finite_floats(0.1, 2.0), min_size=12, max_size=12),
)
def test_allometric_exact_power_law_recovery_and_orthogonality(n, slope, intercept, x_deltas):
    """Exact recovery of noiseless power-law Y = exp(a) * X^b and exact residual orthogonality."""
    x = np.cumsum(x_deltas[:n])
    y_clean = np.exp(intercept) * (x ** slope)
    # Add second noisy-like deterministic trait to test orthogonality
    y_perturbed = y_clean * (1.0 + 0.1 * np.sin(np.arange(n, dtype=np.float64)))
    traits = np.column_stack([y_clean, y_perturbed])

    decomp = allometric_residuals(traits, x, log_transform=True)
    assert not decomp.residuals.flags.writeable
    assert decomp.slopes[0] == pytest.approx(slope, abs=1e-11)
    assert decomp.intercepts[0] == pytest.approx(intercept, abs=1e-11)
    if abs(slope) > 1e-6:
        assert decomp.r_squared[0] == pytest.approx(1.0, abs=1e-10)
    else:
        assert np.allclose(decomp.residuals[:, 0], 0.0, atol=1e-12)

    lx_centered = np.log(x) - np.mean(np.log(x))
    ortho = float(abs(np.dot(decomp.residuals[:, 1], lx_centered)))
    target(ortho, label="allometric_residual_orthogonality_defect")
    assert ortho <= 1e-11


# ============================================================================
# Weighted Morphological Disparity Invariants (Foote 1993)
# ============================================================================

@given(
    n=st.integers(min_value=2, max_value=10),
    scale=finite_floats(0.1, 20.0),
    w_scale=finite_floats(0.1, 20.0),
    shift=st.lists(finite_floats(-10.0, 10.0), min_size=3, max_size=3),
    flat_v=st.lists(finite_floats(-5.0, 5.0), min_size=30, max_size=30),
    raw_w=st.lists(finite_floats(0.1, 10.0), min_size=10, max_size=10),
)
def test_disparity_translation_scale_and_weight_invariances(n, scale, w_scale, shift, flat_v, raw_w):
    """MD_W is translation-invariant, quadratically scale-equivariant, and weight-scale invariant."""
    v = np.array(flat_v[: n * 3], dtype=np.float64).reshape((n, 3))
    w = np.array(raw_w[:n], dtype=np.float64)
    c = np.array(shift, dtype=np.float64)

    base = weighted_morphological_disparity(v, weights=w)
    shifted = weighted_morphological_disparity(v + c[None, :], weights=w)
    scaled = weighted_morphological_disparity(v * scale, weights=w)
    w_scaled = weighted_morphological_disparity(v, weights=w * w_scale)

    assert base.weighted_variance >= 0.0
    assert base.mean_pairwise_distance >= 0.0
    assert 1.0 - 1e-12 <= base.effective_sample_size <= float(n) + 1e-12

    trans_err = abs(shifted.weighted_variance - base.weighted_variance)
    scale_err = abs(scaled.weighted_variance - (scale ** 2) * base.weighted_variance)
    w_err = abs(w_scaled.weighted_variance - base.weighted_variance)
    mpd_scale_err = abs(scaled.mean_pairwise_distance - scale * base.mean_pairwise_distance)

    target(trans_err + w_err, label="disparity_invariance_defect")
    assert trans_err <= 1e-10 * max(1.0, base.weighted_variance)
    assert scale_err <= 1e-10 * max(1.0, scaled.weighted_variance)
    assert w_err <= 1e-10 * max(1.0, base.weighted_variance)
    assert mpd_scale_err <= 1e-10 * max(1.0, scaled.mean_pairwise_distance)


def test_inverse_variance_weights_contracts():
    w = inverse_variance_weights([0.1, 0.2], [1.0, 2.0])
    assert not w.flags.writeable
    assert w[0] == pytest.approx(100.0)
    assert w[1] == pytest.approx(12.5)
    with pytest.raises(ValueError):
        inverse_variance_weights([0.0])
    with pytest.raises(ValueError):
        inverse_variance_weights([0.1], [0.5])
