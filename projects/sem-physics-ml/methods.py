"""Directional, dimensionless conduction and SEM mask quality checks.

NASA EBC annotation label 0 is background, not a chemically identified material.
All conductivity ratios are hypothetical.
"""
from __future__ import annotations
import numpy as np
from scipy import ndimage
from PIL import Image
from physics import conductivity, solve_temperature, effective_conductivity


def orient(array, direction):
    if direction not in ("x", "y"):
        raise ValueError("direction must be x or y")
    return array if direction == "x" else np.rot90(array, axes=(-2, -1))


def directional_solution(mask, values=(1., .4, .05), direction="y"):
    k = conductivity(mask, values)
    rotated = orient(k, direction)
    solved = solve_temperature(rotated)
    output = solved if direction == "x" else np.rot90(solved, k=-1)
    return {"temperature": output,
            "conductivity_proxy": effective_conductivity(rotated, solved),
            "conservation": conservation(rotated, solved),
            "direction": direction}


def conservation(k, T):
    k, T = np.asarray(k, float), np.asarray(T, float)
    if k.ndim != 2 or k.shape != T.shape:
        raise ValueError("k and T must be matching two-dimensional arrays")
    hm = lambda a, b: 2*a*b/(a+b)
    r = np.zeros_like(T)
    r[:, 1:-1] += hm(k[:, 1:-1], k[:, 2:]) * (T[:, 2:] - T[:, 1:-1])
    r[:, 1:-1] += hm(k[:, 1:-1], k[:, :-2]) * (T[:, :-2] - T[:, 1:-1])
    r[1:, 1:-1] += hm(k[1:, 1:-1], k[:-1, 1:-1]) * (T[:-1, 1:-1] - T[1:, 1:-1])
    r[:-1, 1:-1] += hm(k[:-1, 1:-1], k[1:, 1:-1]) * (T[1:, 1:-1] - T[:-1, 1:-1])
    fi = float(np.sum(hm(k[:, 0], k[:, 1])*(T[:, 0]-T[:, 1])))
    fo = float(np.sum(hm(k[:, -2], k[:, -1])*(T[:, -2]-T[:, -1])))
    return {"node_flux_residual_rmse": float(np.sqrt(np.mean(r[:, 1:-1]**2))),
            "incoming_heat_flux": fi, "outgoing_heat_flux": fo,
            "flux_balance_relative_error": abs(fi-fo)/max(abs(fi),1e-12)}


def phase_descriptors(mask, pixel_size_um=None):
    mask = np.asarray(mask)
    conductivity(mask)
    labels, n = ndimage.label(mask == 2, structure=np.ones((3, 3), dtype=int))
    spanning = lambda first, second: bool(np.intersect1d(
        first[first > 0], second[second > 0]).size)
    columns = (mask == 1).sum(axis=0)
    result = {"size": list(mask.shape),
              "phase_area_fraction": {str(i): float(np.mean(mask == i)) for i in range(3)},
              "crack_components_8_connected": int(n),
              "crack_spans_x": spanning(labels[:, 0], labels[:, -1]),
              "crack_spans_y": spanning(labels[0], labels[-1]),
              "oxide_column_coverage_pixels_mean": float(columns.mean()),
              "oxide_column_coverage_pixels_std": float(columns.std()),
              "measurement_note": "Column coverage is not oxide layer thickness without interface identification."}
    if pixel_size_um is not None:
        if pixel_size_um <= 0 or not np.isfinite(pixel_size_um):
            raise ValueError("invalid pixel size")
        result["oxide_column_coverage_um_mean"] = float(columns.mean()*pixel_size_um)
        result["oxide_column_coverage_um_std"] = float(columns.std()*pixel_size_um)
    return result


def audit_resizing(mask, output_size):
    conductivity(mask)
    if output_size < 3:
        raise ValueError("output_size must be >= 3")
    small = np.asarray(Image.fromarray(np.asarray(mask, dtype=np.uint8)).resize(
        (output_size, output_size), Image.Resampling.NEAREST))
    fractions = lambda m: {str(i): float(np.mean(m == i)) for i in range(3)}
    before, after = fractions(mask), fractions(small)
    return {"original_size": list(mask.shape), "resized_size": [output_size, output_size],
            "before": before, "after": after,
            "crack_abs_fraction_change": abs(before["2"]-after["2"]),
            "crack_lost_entirely": bool(np.any(mask == 2) and not np.any(small == 2)),
            "coarse_mask": small}


def per_class_iou(truth, prediction):
    conductivity(truth)
    conductivity(prediction)
    if truth.shape != prediction.shape:
        raise ValueError("shape mismatch")
    result = {}
    for i in range(3):
        a, b = truth == i, prediction == i
        union = np.count_nonzero(a | b)
        result[str(i)] = float(np.count_nonzero(a & b)/union) if union else None
    return result
