"""Physics-informed CNN surrogate for a discretized heat equation."""
from __future__ import annotations

import torch
from torch import nn
import torch.nn.functional as F


class TransportCNN(nn.Module):
    """Input: one-hot phase mask + normalized conductivity + x/y coordinates.

    Boundary temperatures are embedded, so the network cannot violate them.
    """
    def __init__(self, width=24):
        super().__init__()
        self.network = nn.Sequential(
            nn.Conv2d(6, width, 3, padding=1), nn.GELU(),
            nn.Conv2d(width, width, 3, padding=2, dilation=2), nn.GELU(),
            nn.Conv2d(width, width, 3, padding=4, dilation=4), nn.GELU(),
            nn.Conv2d(width, width, 3, padding=8, dilation=8), nn.GELU(),
            nn.Conv2d(width, width, 1), nn.GELU(),
            nn.Conv2d(width, 1, 1),
        )

    def forward(self, labels: torch.Tensor, k: torch.Tensor) -> torch.Tensor:
        if labels.ndim != 3 or k.shape != labels.shape:
            raise ValueError("labels and conductivity must both have shape (batch,H,W)")
        n, h, w = labels.shape
        x = torch.linspace(0, 1, w, device=k.device, dtype=k.dtype).view(1, 1, 1, w).expand(n, 1, h, w)
        y = torch.linspace(0, 1, h, device=k.device, dtype=k.dtype).view(1, 1, h, 1).expand(n, 1, h, w)
        classes = F.one_hot(labels.long(), 3).permute(0, 3, 1, 2).to(dtype=k.dtype)
        raw = self.network(torch.cat([classes, k[:, None], x, y], dim=1)).squeeze(1)
        profile = 1 - x.squeeze(1)
        return profile + 2.5 * x.squeeze(1) * (1-x.squeeze(1)) * torch.tanh(raw)


def physics_residual(T: torch.Tensor, k: torch.Tensor) -> torch.Tensor:
    """Finite-volume div(k grad T) for all non-Dirichlet nodes."""
    if T.shape != k.shape or T.ndim != 3:
        raise ValueError("T and k must be batch,H,W tensors")
    center_k = k[:, :, 1:-1]
    center_t = T[:, :, 1:-1]
    def harmonic(a, b):
        return 2*a*b / (a+b)
    right = harmonic(center_k, k[:, :, 2:])*(T[:, :, 2:]-center_t)
    left = harmonic(center_k, k[:, :, :-2])*(T[:, :, :-2]-center_t)
    top = torch.zeros_like(center_t)
    bottom = torch.zeros_like(center_t)
    top[:, 1:, :] = harmonic(center_k[:, 1:, :], center_k[:, :-1, :])*(center_t[:, :-1, :]-center_t[:, 1:, :])
    bottom[:, :-1, :] = harmonic(center_k[:, :-1, :], center_k[:, 1:, :])*(center_t[:, 1:, :]-center_t[:, :-1, :])
    return left+right+top+bottom
