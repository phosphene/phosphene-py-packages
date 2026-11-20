"""holonomy.morphometrics.procrustes - Kendall shape-space preshape and Procrustes alignment.

Pure functional geometric morphometrics in Kendall's shape space (zero disk I/O,
strictly immutable read-only arrays).

Genealogy:
    Rung: 1/2 (Euclidean centering/scaling and SVD-based orthogonal Procrustes rotation
        on SO(m) / O(m), plus iterative Generalized Procrustes Analysis).
    Literature: Kendall (1984) Bull. London Math. Soc. 16:81–121;
        Gower (1975) Psychometrika 40:33–51; Rohlf & Slice (1990) Syst. Zool. 39:40–59.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Sequence

import numpy as np

from phosphene.holonomy.morphometrics.configuration import Configuration


def _readonly_copy(arr: np.ndarray) -> np.ndarray:
    out = np.array(arr, dtype=np.float64, copy=True)
    out.flags.writeable = False
    return out


@dataclass(frozen=True)
class ProcrustesAlignment:
    """Immutable result of ordinary Procrustes superimposition of source onto target.

    Dimensions:
        aligned_landmarks: Read-only (k, m) preshape coordinates aligned to target [dimensionless].
        rotation_matrix: Read-only (m, m) orthogonal rotation matrix R in SO(m) (or O(m)).
        procrustes_distance: [dimensionless] Partial Procrustes Euclidean chord distance d_P in [0, 2].
        riemannian_distance: [radians] Full Kendall shape-space geodesic distance rho in [0, pi/2].
    """

    aligned_landmarks: np.ndarray
    rotation_matrix: np.ndarray
    procrustes_distance: float
    riemannian_distance: float

    def __post_init__(self) -> None:
        object.__setattr__(self, "aligned_landmarks", _readonly_copy(self.aligned_landmarks))
        object.__setattr__(self, "rotation_matrix", _readonly_copy(self.rotation_matrix))


@dataclass(frozen=True)
class ProcrustesConsensus:
    """Immutable result of Generalized Procrustes Analysis (GPA) across a specimen sample.

    Dimensions:
        mean_shape: Read-only (k, m) unit-norm consensus preshape [dimensionless].
        aligned_shapes: Tuple of N read-only (k, m) aligned preshapes [dimensionless].
        procrustes_distances: Read-only (N,) array of partial Procrustes distances to mean_shape.
        converged: [bool] True if consensus shift fell below ``tol`` within ``max_iter``.
        iterations: [int] Number of GPA iterations executed.
    """

    mean_shape: np.ndarray
    aligned_shapes: tuple[np.ndarray, ...]
    procrustes_distances: np.ndarray
    converged: bool
    iterations: int

    def __post_init__(self) -> None:
        object.__setattr__(self, "mean_shape", _readonly_copy(self.mean_shape))
        object.__setattr__(
            self,
            "aligned_shapes",
            tuple(_readonly_copy(s) for s in self.aligned_shapes),
        )
        object.__setattr__(self, "procrustes_distances", _readonly_copy(self.procrustes_distances))


def preshape(config: Configuration) -> np.ndarray:
    """Center and scale a landmark configuration onto Kendall's unit preshape sphere.

    Genealogy:
        Rung: 1 (Read-only 2D ``numpy`` normalization).
        Literature: Kendall (1984); Dryden & Mardia (2016) Statistical Shape Analysis.

    Objective:
        Z = (X - mean(X, axis=0)) / ||X - mean(X, axis=0)||_F,   ||Z||_F == 1

    Dimensions:
        config: Immutable Configuration with landmarks of shape (k, m) [L].
        Returns: Read-only (k, m) float64 preshape matrix [dimensionless] with Frobenius norm 1.

    Boundary & Falsification Semantics:
        - Degenerate configuration (centroid_size == 0) or non-finite landmarks -> raises ValueError.

    Invariants & Oracles:
        - Exact translation invariance: preshape(X + t) == preshape(X).
        - Exact positive scale invariance: preshape(c * X) == preshape(X) for c > 0.
        - Unit Frobenius norm: ||Z||_F == 1 and column means == 0.
    """
    coords = config.landmarks
    if coords.ndim != 2 or coords.shape[0] < 2 or coords.shape[1] < 1:
        raise ValueError(f"Configuration landmarks must be 2D (k>=2, m>=1), got shape {coords.shape}")
    if not np.all(np.isfinite(coords)):
        raise ValueError("Configuration landmarks must contain only finite values")

    centered = coords - np.mean(coords, axis=0, keepdims=True)
    cs = float(np.linalg.norm(centered))
    if cs <= 0.0 or not math.isfinite(cs):
        raise ValueError("Degenerate landmark configuration with zero centroid size")

    z = centered / cs
    z.flags.writeable = False
    return z


def _orthogonal_rotation(z_source: np.ndarray, z_target: np.ndarray, allow_reflection: bool) -> np.ndarray:
    """Optimal orthogonal matrix R minimizing ||z_source @ R - z_target||_F via SVD."""
    cross = z_source.T @ z_target
    u, _s, vt = np.linalg.svd(cross)
    r = u @ vt
    if not allow_reflection and np.linalg.det(r) < 0.0:
        u_adj = u.copy()
        u_adj[:, -1] *= -1.0
        r = u_adj @ vt
    return r


def procrustes_alignment(
    source: Configuration,
    target: Configuration,
    allow_reflection: bool = False,
) -> ProcrustesAlignment:
    """Ordinary Procrustes superimposition of ``source`` onto ``target`` in Kendall shape space.

    Genealogy:
        Rung: 2 (SVD orthogonal Procrustes rotation on SO(m) or O(m)).
        Literature: Gower (1975); Rohlf & Slice (1990); Dryden & Mardia (2016).

    Objective:
        R* = argmin_{R in SO(m)} ||Z_source R - Z_target||_F
        d_P = ||Z_source R* - Z_target||_F
        rho = arccos(clip(<Z_source R*, Z_target>_F, -1, 1))

    Dimensions:
        source, target: Configurations of identical shape (k, m) [L].
        Returns: ``ProcrustesAlignment`` with dimensionless chord & geodesic distances.

    Boundary & Falsification Semantics:
        - Mismatched shapes or degenerate zero-size configurations -> raises ValueError.

    Invariants & Oracles:
        - Strict invariance under translation, positive scaling, and proper rotation R in SO(m).
        - Orthogonality: ||R^T R - I||_F <= 1e-12 and det(R) == +1 when allow_reflection=False.
        - Symmetry: d_P(A, B) == d_P(B, A); Identity: d_P(A, A) == 0.
    """
    if source.landmarks.shape != target.landmarks.shape:
        raise ValueError(
            f"Shape mismatch: source {source.landmarks.shape} != target {target.landmarks.shape}"
        )

    z_src = preshape(source)
    z_tgt = preshape(target)
    r = _orthogonal_rotation(z_src, z_tgt, allow_reflection=allow_reflection)
    aligned = z_src @ r
    d_p = float(np.linalg.norm(aligned - z_tgt))
    cos_rho = float(np.clip(np.sum(aligned * z_tgt), -1.0, 1.0))
    rho = float(math.acos(cos_rho))

    return ProcrustesAlignment(
        aligned_landmarks=aligned,
        rotation_matrix=r,
        procrustes_distance=d_p,
        riemannian_distance=rho,
    )


def generalized_procrustes(
    configs: Sequence[Configuration],
    allow_reflection: bool = False,
    max_iter: int = 50,
    tol: float = 1e-10,
) -> ProcrustesConsensus:
    """Generalized Procrustes Analysis (GPA) computing sample consensus shape and residuals.

    Genealogy:
        Rung: 2 (Iterative SVD alignment onto unit-norm consensus shape).
        Literature: Gower (1975); Rohlf & Slice (1990).

    Objective:
        Iteratively rotates preshapes {Z_i} onto unit-norm mean shape M until
        ||M^(t+1) - M^(t)||_F <= tol.

    Dimensions:
        configs: Non-empty sequence of Configurations of identical shape (k, m) [L].
        Returns: ``ProcrustesConsensus`` with read-only arrays.

    Boundary & Falsification Semantics:
        - Empty sequence, mismatched shapes, max_iter < 1, or tol <= 0 -> raises ValueError.
    """
    if len(configs) == 0:
        raise ValueError("configs must be non-empty")
    if max_iter < 1:
        raise ValueError(f"max_iter must be >= 1, got {max_iter}")
    if not math.isfinite(tol) or tol <= 0.0:
        raise ValueError(f"tol must be finite and > 0.0, got {tol}")

    ref_shape = configs[0].landmarks.shape
    preshapes = []
    for idx, cfg in enumerate(configs):
        if cfg.landmarks.shape != ref_shape:
            raise ValueError(f"Configuration {idx} shape {cfg.landmarks.shape} != expected {ref_shape}")
        preshapes.append(preshape(cfg))

    mean = preshapes[0].copy()
    aligned = [z.copy() for z in preshapes]
    converged = False
    iters = 0

    for it in range(1, max_iter + 1):
        iters = it
        aligned = [z @ _orthogonal_rotation(z, mean, allow_reflection=allow_reflection) for z in preshapes]
        new_mean = np.mean(aligned, axis=0)
        norm_m = float(np.linalg.norm(new_mean))
        if norm_m > 0.0:
            new_mean = new_mean / norm_m
        shift = float(np.linalg.norm(new_mean - mean))
        mean = new_mean
        if shift <= tol:
            converged = True
            break

    dists = np.array([float(np.linalg.norm(z - mean)) for z in aligned], dtype=np.float64)
    return ProcrustesConsensus(
        mean_shape=mean,
        aligned_shapes=tuple(aligned),
        procrustes_distances=dists,
        converged=converged,
        iterations=iters,
    )


__all__ = [
    "ProcrustesAlignment",
    "ProcrustesConsensus",
    "preshape",
    "procrustes_alignment",
    "generalized_procrustes",
]
