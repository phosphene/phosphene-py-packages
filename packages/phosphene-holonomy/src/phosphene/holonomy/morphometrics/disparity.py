"""holonomy.morphometrics.disparity - Allometric residualization and weighted morphological disparity.

Pure functional continuous morphospace disparity primitives (zero disk I/O, zero
taxonomic hardcoding, strictly immutable read-only outputs).

Genealogy:
    Rung: 1 (Closed-form OLS allometric residualization & weighted variance/pairwise
        disparity metrics in continuous trait space).
    Literature: Huxley (1932) Problems of Relative Growth; Foote (1993) Paleobiology 19:185–204;
        Zelditch, Swiderski, & Sheets (2012) Geometric Morphometrics for Biologists.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Sequence

import numpy as np


def _readonly_copy(arr: np.ndarray) -> np.ndarray:
    out = np.array(arr, dtype=np.float64, copy=True)
    out.flags.writeable = False
    return out


@dataclass(frozen=True)
class AllometricDecomposition:
    """Immutable OLS allometric regression decomposition of continuous traits on a size proxy.

    Objective:
        Y_tilde = intercept + slope * X_tilde + residual
        (where Y_tilde = ln(Y), X_tilde = ln(X) when ``log_transform=True``).

    Dimensions:
        slopes: Read-only (D,) dimensionless allometric scaling exponents (when log-transformed).
        intercepts: Read-only (D,) regression intercepts.
        residuals: Read-only (N, D) size-free allometric residual vectors.
        r_squared: Read-only (D,) coefficient of determination per trait in [0, 1].
    """

    slopes: np.ndarray
    intercepts: np.ndarray
    residuals: np.ndarray
    r_squared: np.ndarray

    def __post_init__(self) -> None:
        object.__setattr__(self, "slopes", _readonly_copy(self.slopes))
        object.__setattr__(self, "intercepts", _readonly_copy(self.intercepts))
        object.__setattr__(self, "residuals", _readonly_copy(self.residuals))
        object.__setattr__(self, "r_squared", _readonly_copy(self.r_squared))


@dataclass(frozen=True)
class MorphologicalDisparity:
    """Immutable continuous morphological disparity summary (Foote 1993 weighted variance & MPD).

    Dimensions:
        weighted_variance (MD_W): [trait_unit^2] Weighted sum of variances around weighted centroid.
        mean_pairwise_distance (MPD_W): [trait_unit] Weighted mean pairwise Euclidean distance.
        weighted_centroid: Read-only (D,) weighted morphospace centroid [trait_unit].
        effective_sample_size: [specimens] Kish effective sample size (sum w)^2 / sum(w^2).
        num_specimens: [specimens] Raw specimen count N.
    """

    weighted_variance: float
    mean_pairwise_distance: float
    weighted_centroid: np.ndarray
    effective_sample_size: float
    num_specimens: int

    def __post_init__(self) -> None:
        object.__setattr__(self, "weighted_centroid", _readonly_copy(self.weighted_centroid))


def inverse_variance_weights(
    measurement_errors: Sequence[float] | np.ndarray,
    taphonomic_fragilities: Sequence[float] | np.ndarray | None = None,
) -> np.ndarray:
    """Inverse-variance precision weights attenuated by taphonomic fragility.

    Genealogy:
        Rung: 1 (Read-only 1D ``numpy`` weight vector).

    Objective:
        w_i = 1 / (sigma_i^2 * f_i)

    Dimensions:
        measurement_errors (sigma_i): [trait_unit or CV] Strictly positive standard errors (> 0).
        taphonomic_fragilities (f_i): [dimensionless] Optional fragility penalty factors (>= 1.0).
        Returns: Read-only (N,) strictly positive float64 weight array.

    Boundary & Falsification Semantics:
        - Empty sequence, non-positive sigma_i, f_i < 1.0, mismatched lengths, or non-finite -> raises ValueError.
    """
    errs = np.asarray(measurement_errors, dtype=np.float64)
    if errs.ndim != 1 or len(errs) == 0:
        raise ValueError("measurement_errors must be a non-empty 1D sequence")
    if not np.all(np.isfinite(errs)) or np.any(errs <= 0.0):
        raise ValueError("All measurement_errors must be finite and > 0.0")

    if taphonomic_fragilities is None:
        frag = np.ones_like(errs)
    else:
        frag = np.asarray(taphonomic_fragilities, dtype=np.float64)
        if frag.shape != errs.shape:
            raise ValueError(
                f"taphonomic_fragilities shape {frag.shape} != measurement_errors shape {errs.shape}"
            )
        if not np.all(np.isfinite(frag)) or np.any(frag < 1.0):
            raise ValueError("All taphonomic_fragilities must be finite and >= 1.0")

    weights = 1.0 / ((errs * errs) * frag)
    weights.flags.writeable = False
    return weights


def allometric_residuals(
    traits: np.ndarray,
    size_proxy: Sequence[float] | np.ndarray,
    log_transform: bool = True,
) -> AllometricDecomposition:
    """Closed-form OLS allometric residualization removing static/evolutionary size scaling.

    Genealogy:
        Rung: 1 (Closed-form scalar/vector OLS covariance projection).
        Collapses To: Mean-centered traits when ``size_proxy`` has zero variance.
        Literature: Huxley (1932); Bookstein (1991); Zelditch et al. (2012).

    Objective:
        b_d = Cov(x, y_d) / Var(x),   a_d = mean(y_d) - b_d * mean(x)
        r_{i,d} = y_{i,d} - (a_d + b_d * x_i)

    Dimensions:
        traits: 2D array (N, D) of continuous osteometric/morphometric measurements.
        size_proxy: 1D array (N,) of body size or centroid size measurements.
        log_transform: If True, applies natural log to both traits and size_proxy (requires > 0).
        Returns: ``AllometricDecomposition`` with read-only arrays.

    Boundary & Falsification Semantics:
        - N < 2, mismatched lengths, non-finite inputs, or <= 0 values when log_transform=True -> raises ValueError.

    Invariants & Oracles:
        - Exact residual zero-mean: mean(residuals, axis=0) == 0.
        - Exact orthogonality: <residuals[:, d], x - mean(x)> == 0 to machine precision.
    """
    y_raw = np.asarray(traits, dtype=np.float64)
    x_raw = np.asarray(size_proxy, dtype=np.float64)
    if y_raw.ndim != 2 or y_raw.shape[0] < 2 or y_raw.shape[1] < 1:
        raise ValueError(f"traits must be 2D (N>=2, D>=1), got shape {y_raw.shape}")
    if x_raw.ndim != 1 or x_raw.shape[0] != y_raw.shape[0]:
        raise ValueError(f"size_proxy must be 1D of length {y_raw.shape[0]}, got shape {x_raw.shape}")
    if not (np.all(np.isfinite(y_raw)) and np.all(np.isfinite(x_raw))):
        raise ValueError("traits and size_proxy must contain only finite values")

    if log_transform:
        if np.any(y_raw <= 0.0) or np.any(x_raw <= 0.0):
            raise ValueError("All traits and size_proxy values must be strictly > 0.0 when log_transform=True")
        y = np.log(y_raw)
        x = np.log(x_raw)
    else:
        y = y_raw
        x = x_raw

    x_mean = float(np.mean(x))
    y_mean = np.mean(y, axis=0)
    dx = x - x_mean
    dy = y - y_mean
    ss_x = float(np.dot(dx, dx))

    if ss_x <= 0.0:
        slopes = np.zeros(y.shape[1], dtype=np.float64)
        intercepts = y_mean.copy()
        residuals = dy.copy()
        r2 = np.zeros(y.shape[1], dtype=np.float64)
    else:
        slopes = (dx @ dy) / ss_x
        intercepts = y_mean - slopes * x_mean
        fitted = intercepts[None, :] + np.outer(x, slopes)
        residuals = y - fitted
        ss_tot = np.sum(dy * dy, axis=0)
        ss_res = np.sum(residuals * residuals, axis=0)
        r2 = np.where(ss_tot > 0.0, np.clip(1.0 - ss_res / np.where(ss_tot > 0.0, ss_tot, 1.0), 0.0, 1.0), 0.0)

    return AllometricDecomposition(
        slopes=slopes,
        intercepts=intercepts,
        residuals=residuals,
        r_squared=r2,
    )


def weighted_morphological_disparity(
    vectors: np.ndarray,
    weights: Sequence[float] | np.ndarray | None = None,
) -> MorphologicalDisparity:
    """Weighted continuous morphological disparity (Foote's MD_W & mean pairwise distance MPD_W).

    Genealogy:
        Rung: 1 (Exact closed-form weighted variance and pairwise distance reduction).
        Collapses To: Unweighted Foote (1993) sum of variances when ``weights is None``.
        Literature: Foote (1993) Paleobiology 19(2):185–204; Zelditch et al. (2012).

    Objective:
        centroid = (sum_i w_i v_i) / (sum_i w_i)
        MD_W     = (sum_i w_i ||v_i - centroid||_2^2) / (sum_i w_i)
        MPD_W    = (sum_{i < j} w_i w_j ||v_i - v_j||_2) / (sum_{i < j} w_i w_j)
        N_eff    = (sum_i w_i)^2 / (sum_i w_i^2)

    Dimensions:
        vectors: 2D array (N, D) of continuous trait or allometric-residual vectors [unit].
        weights: Optional 1D array (N,) of strictly positive precision weights (> 0).
        Returns: ``MorphologicalDisparity`` bundle.

    Boundary & Falsification Semantics:
        - Empty vectors, non-finite values, mismatched weight lengths, or weights <= 0 -> raises ValueError.
        - Single specimen (N == 1) -> MD_W == 0.0, MPD_W == 0.0, N_eff == 1.0.

    Invariants & Oracles:
        - Translation invariance: MD_W(V + c) == MD_W(V) and MPD_W(V + c) == MPD_W(V).
        - Scale equivariance: MD_W(c * V) == c^2 * MD_W(V) and MPD_W(c * V) == |c| * MPD_W(V).
        - Weight scale invariance: invariant under w -> c * w for c > 0.
        - Strict non-negativity: MD_W >= 0.0, MPD_W >= 0.0, 1 <= N_eff <= N.
    """
    v = np.asarray(vectors, dtype=np.float64)
    if v.ndim != 2 or v.shape[0] < 1 or v.shape[1] < 1:
        raise ValueError(f"vectors must be 2D (N>=1, D>=1), got shape {v.shape}")
    if not np.all(np.isfinite(v)):
        raise ValueError("vectors must contain only finite values")

    n = v.shape[0]
    if weights is None:
        w = np.ones(n, dtype=np.float64)
    else:
        w = np.asarray(weights, dtype=np.float64)
        if w.shape != (n,):
            raise ValueError(f"weights must have shape ({n},), got {w.shape}")
        if not np.all(np.isfinite(w)) or np.any(w <= 0.0):
            raise ValueError("All weights must be finite and > 0.0")

    w_sum = float(np.sum(w))
    w_sq_sum = float(np.sum(w * w))
    n_eff = (w_sum * w_sum) / w_sq_sum
    centroid = (w @ v) / w_sum

    if n == 1:
        return MorphologicalDisparity(
            weighted_variance=0.0,
            mean_pairwise_distance=0.0,
            weighted_centroid=centroid,
            effective_sample_size=1.0,
            num_specimens=1,
        )

    diff = v - centroid[None, :]
    sq_norms = np.sum(diff * diff, axis=1)
    md_w = float(np.dot(w, sq_norms) / w_sum)

    # Pairwise weighted Euclidean distance across i < j
    num_mpd = 0.0
    den_mpd = 0.0
    for i in range(n - 1):
        d_ij = np.linalg.norm(v[i + 1 :] - v[i], axis=1)
        w_ij = w[i] * w[i + 1 :]
        num_mpd += float(np.dot(w_ij, d_ij))
        den_mpd += float(np.sum(w_ij))
    mpd_w = num_mpd / den_mpd if den_mpd > 0.0 else 0.0

    return MorphologicalDisparity(
        weighted_variance=md_w,
        mean_pairwise_distance=mpd_w,
        weighted_centroid=centroid,
        effective_sample_size=float(n_eff),
        num_specimens=n,
    )


__all__ = [
    "AllometricDecomposition",
    "MorphologicalDisparity",
    "inverse_variance_weights",
    "allometric_residuals",
    "weighted_morphological_disparity",
]
