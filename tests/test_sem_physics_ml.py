from pathlib import Path
import sys

import numpy as np
import pytest
import torch

P = Path(__file__).resolve().parents[1] / 'projects' / 'sem-physics-ml'
sys.path.insert(0, str(P))
from physics import conductivity, solve_temperature, effective_conductivity, synthetic_masks
from model import TransportCNN, physics_residual


def test_uniform_conductivity_exact():
    k = np.ones((12, 12))*0.4
    T = solve_temperature(k)
    expected = 1-np.arange(12)/11
    np.testing.assert_allclose(T, np.broadcast_to(expected[None, :], T.shape), atol=1e-12)
    assert effective_conductivity(k, T) == pytest.approx(0.4, abs=1e-10)
    residual = physics_residual(torch.tensor(T)[None], torch.tensor(k)[None])
    assert torch.max(residual.abs()).item() < 1e-10


def test_series_layers_and_energy_balance():
    mask = np.zeros((12, 24), dtype=int)
    mask[:, 8:16] = 1
    k = conductivity(mask)
    T = solve_temperature(k)
    flux_in = effective_conductivity(k, T)
    flux_out = float(np.mean(2*k[:, -1]*k[:, -2]/(k[:, -1]+k[:, -2])*(T[:, -2]-T[:, -1]))*(k.shape[1]-1))
    assert flux_in > 0
    assert flux_in == pytest.approx(flux_out, rel=1e-10)
    assert 0.4 <= flux_in <= 1.0


def test_invalid_phases_rejected():
    with pytest.raises(ValueError):
        conductivity(np.ones((5, 5), dtype=np.uint8)*3)
    with pytest.raises(ValueError):
        conductivity(np.ones((5, 5), dtype=np.uint8), (1, 0, 0.1))


def test_cnn_boundaries_gradients_and_shapes():
    labels = torch.tensor(synthetic_masks(2, 16, 2), dtype=torch.long)
    k = torch.tensor(np.stack([conductivity(a) for a in labels.numpy()]), dtype=torch.float)
    net = TransportCNN(width=8)
    out = net(labels, k)
    assert out.shape == k.shape
    assert torch.all(out[:, :, 0] == 1)
    assert torch.all(out[:, :, -1] == 0)
    physics_residual(out, k).square().mean().backward()
    assert any(p.grad is not None for p in net.parameters())


def test_inference_with_saved_synthetic_checkpoint():
    from predict import run
    checkpoint = P / 'results' / 'transport_cnn_synthetic.pt'
    if not checkpoint.exists():
        pytest.skip('Local checkpoint not generated: run train.py --save-checkpoint')
    mask = synthetic_masks(1, 24, 123)[0]
    result = run(mask, checkpoint)
    assert sum(result['phase_area_fractions'].values()) == pytest.approx(1, abs=1e-5)
    assert result['pde_residual_rmse'] >= 0
    assert result['numerical_reference_conductivity_proxy'] > 0


def test_missing_sem_checkpoint_raises(tmp_path):
    from predict import infer_segmentation
    with pytest.raises(FileNotFoundError, match='Trained SEM checkpoint not found'):
        infer_segmentation(tmp_path / 'scan.tif', tmp_path / 'missing.pt', 24)
