"""Finite-volume heat conduction on a labelled 2-D microstructure.

SEM labels follow NASA EBC: 0 background, 1 oxide, 2 crack.
Conductivities are assumptions, not material measurements.
"""
from __future__ import annotations

import numpy as np
from scipy.sparse import lil_matrix
from scipy.sparse.linalg import spsolve

DEFAULT_K = (1.0, 0.4, 0.05)


def conductivity(mask: np.ndarray, values=DEFAULT_K) -> np.ndarray:
    labels = np.asarray(mask)
    if labels.ndim != 2 or labels.shape[0] < 3 or labels.shape[1] < 3:
        raise ValueError("Expected a 2-D integer mask at least 3x3")
    if not np.issubdtype(labels.dtype, np.integer) or np.any((labels < 0) | (labels > 2)):
        raise ValueError("NASA EBC labels must be integers 0, 1, or 2")
    k = np.asarray(values, dtype=float)
    if k.shape != (3,) or not np.all(np.isfinite(k)) or np.any(k <= 0):
        raise ValueError("Provide three positive finite phase conductivities")
    return k[labels]


def harmonic(a, b):
    return 2 * a * b / (a + b)


def solve_temperature(k: np.ndarray) -> np.ndarray:
    """Solve div(k grad T)=0; T(left)=1, T(right)=0; top/bottom no-flux.

    Conductance between adjacent nodes is the harmonic mean of their
    conductivities. Uniform spacing is assumed in both dimensions.
    """
    k = np.asarray(k, dtype=float)
    if k.ndim != 2 or min(k.shape) < 3 or not np.all(np.isfinite(k)) or np.any(k <= 0):
        raise ValueError("k must be a positive finite 2-D array >= 3x3")
    h, w = k.shape
    n = h * (w - 2)
    A = lil_matrix((n, n), dtype=float)
    b = np.zeros(n)
    def index(y, x):
        return y * (w - 2) + (x - 1)
    for y in range(h):
        for x in range(1, w - 1):
            i = index(y, x)
            for dy, dx in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                yy, xx = y + dy, x + dx
                if not (0 <= yy < h and 0 <= xx < w):
                    continue
                face = harmonic(k[y, x], k[yy, xx])
                A[i, i] += face
                if xx == 0:
                    b[i] += face
                elif xx == w - 1:
                    pass
                else:
                    A[i, index(yy, xx)] -= face
    T = np.empty_like(k)
    T[:, 0] = 1.0
    T[:, -1] = 0.0
    T[:, 1:-1] = spsolve(A.tocsr(), b).reshape(h, w - 2)
    return T


def effective_conductivity(k: np.ndarray, T: np.ndarray) -> float:
    """Left boundary heat flux, scaled to unit-length sample conductivity."""
    if k.shape != T.shape:
        raise ValueError("conductivity and temperature shapes differ")
    return float(np.mean(harmonic(k[:, 0], k[:, 1]) * (T[:, 0] - T[:, 1])) * (k.shape[1] - 1))


def synthetic_masks(count: int, size: int, seed: int) -> np.ndarray:
    """Artificial 3-class maps for code validation only (not SEM measurements)."""
    rng = np.random.default_rng(seed)
    out = np.zeros((count, size, size), dtype=np.uint8)
    for n in range(count):
        mask = out[n]
        y, x = np.mgrid[:size, :size]
        band = rng.integers(size // 4, size // 2)
        thickness = rng.integers(max(2, size // 6), max(3, size // 3))
        wave = rng.uniform(0.0, 2.0) * np.sin(x / rng.uniform(2.0, 6.0) + rng.uniform(0, 6))
        mask[(y >= band + wave) & (y < band + thickness + wave)] = 1
        if n % 3 == 0:
            mask[(x > size // 3) & (x < size // 3 + 2) & (y > size // 4)] = 1
        for _ in range(int(rng.integers(1, 4))):
            cx, cy = int(rng.integers(2, size - 2)), int(rng.integers(2, size - 2))
            if rng.integers(2):
                mask[max(cy-1, 0):min(cy+2, size), max(cx-3, 0):min(cx+4, size)] = 2
            else:
                mask[max(cy-3, 0):min(cy+4, size), max(cx-1, 0):min(cx+2, size)] = 2
    return out
