"""Trained SEM U-Net -> 3-phase mask -> physics-informed transport surrogate.

No random-weight fallback. Use --mask for NASA EBC annotations.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image
import torch

from model import TransportCNN, physics_residual
from physics import conductivity, effective_conductivity, solve_temperature, synthetic_masks

ROOT = Path(__file__).resolve().parents[2]
PROJECT = Path(__file__).resolve().parent


def read_mask(path: Path, shape: int) -> np.ndarray:
    if not path.is_file():
        raise FileNotFoundError(f"Mask not found: {path}")
    with Image.open(path) as image:
        labels = np.asarray(image.resize((shape, shape), resample=Image.Resampling.NEAREST))
    if labels.ndim != 2 or not np.isin(labels, [0, 1, 2]).all():
        raise ValueError("NASA EBC mask must be 2-D, with integer labels 0/1/2")
    return labels.astype(np.uint8)


def infer_segmentation(image_path: Path, checkpoint_path: Path, size: int) -> np.ndarray:
    """Load the U-Net architecture and normalization saved by the SEM project."""
    if not checkpoint_path.is_file():
        raise FileNotFoundError(f"Trained SEM checkpoint not found: {checkpoint_path}. "
                                "Run scripts/run_sem_segmentation.py or supply your existing .pt file.")
    if not image_path.is_file():
        raise FileNotFoundError(f"SEM image not found: {image_path}")
    sys.path.insert(0, str(ROOT / 'src'))
    from microscopy_cv_research.models.segmentation import create_segmentation_model

    saved = torch.load(checkpoint_path, map_location='cpu', weights_only=True)
    if not isinstance(saved, dict) or 'model_state' not in saved or 'config' not in saved:
        raise ValueError("Expected a checkpoint containing model_state and config")
    cfg = saved['config']
    if cfg.get('model_name', 'unet_small') != 'unet_small' or int(cfg.get('num_classes', 3)) != 3:
        raise ValueError("This adapter supports the trained NASA EBC UNetSmall, 3 classes")
    network = create_segmentation_model('unet_small', num_classes=3,
        base_channels=int(cfg.get('base_channels', 32)), dropout=float(cfg.get('dropout', .1)))
    network.load_state_dict(saved['model_state'], strict=True)
    network.eval()
    image_size = int(cfg.get('image_size', 256))
    with Image.open(image_path) as image:
        rgb = np.asarray(image.convert('RGB').resize((image_size, image_size), Image.Resampling.BILINEAR), dtype=np.float32)/255
    tensor = (torch.from_numpy(rgb).permute(2,0,1)[None] -
              torch.tensor([0.485,0.456,0.406]).view(1,3,1,1))/torch.tensor([0.229,0.224,0.225]).view(1,3,1,1)
    with torch.inference_mode():
        pred = network(tensor).argmax(dim=1)[0].numpy().astype('uint8')
    return np.asarray(Image.fromarray(pred).resize((size, size), Image.Resampling.NEAREST), dtype=np.uint8)


def run(mask: np.ndarray, transport_checkpoint: Path, phase_conductivities=None) -> dict:
    if not transport_checkpoint.is_file():
        raise FileNotFoundError(f"Transport ANN checkpoint not found: {transport_checkpoint}. "
                                "First run: python projects/sem-physics-ml/train.py --save-checkpoint")
    saved = torch.load(transport_checkpoint, map_location='cpu', weights_only=True)
    if saved.get('training_type') != 'synthetic':
        raise ValueError("Unrecognized transport model provenance")
    expected_size = int(saved['size'])
    if mask.shape != (expected_size, expected_size):
        raise ValueError(f"Mask should be resized to {(expected_size,expected_size)}")
    k_values = tuple(phase_conductivities) if phase_conductivities is not None else tuple(saved['relative_conductivities'])
    k = conductivity(mask, k_values)
    net = TransportCNN(width=int(saved['width']))
    net.load_state_dict(saved['model_state'], strict=True)
    net.eval()
    labels = torch.tensor(mask.copy(), dtype=torch.long)[None]
    kt = torch.tensor(k, dtype=torch.float32)[None]
    with torch.inference_mode():
        predicted = net(labels, kt)
        residual = float(physics_residual(predicted, kt).square().mean().sqrt())
    T = predicted[0].numpy()
    reference = solve_temperature(k)
    return {
        'source': 'user-provided SEM image/checkpoint or class mask (see input_type)',
        'mask_resolution': list(mask.shape),
        'phase_area_fractions': {str(label):round(float(np.mean(mask==label)),6) for label in range(3)},
        'assumed_relative_conductivities': list(k_values),
        'piml_conductivity_proxy':round(effective_conductivity(k,T),6),
        'numerical_reference_conductivity_proxy':round(effective_conductivity(k,reference),6),
        'piml_vs_reference_temperature_mae':round(float(np.mean(np.abs(T-reference))),6),
        'pde_residual_rmse':round(residual,6),
        'warning': '2-D simulated heat transport with assumed conductivity values; not measured material properties. Check orientation, segmentation error and grid coarsening.'
    }


def main():
    parser = argparse.ArgumentParser(description='SEM U-Net/label map to physics-informed surrogate prediction')
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--image', type=Path, help='SEM image; requires your trained U-Net checkpoint')
    group.add_argument('--mask', type=Path, help='NASA 0/1/2 phase mask')
    group.add_argument('--demo', action='store_true', help='Synthetic sanity-check only')
    parser.add_argument('--sem-checkpoint', type=Path, default=ROOT/'models/checkpoints/sem_ebc_unet.pt')
    parser.add_argument('--transport-checkpoint', type=Path, default=PROJECT/'results/transport_cnn_synthetic.pt')
    parser.add_argument('--k', nargs=3, type=float, default=None, metavar=('BACKGROUND','OXIDE','CRACK'))
    parser.add_argument('--out', type=Path, default=PROJECT/'results/inference.json')
    args = parser.parse_args()
    if not args.transport_checkpoint.is_file():
        parser.error('Transport CNN weights missing. Run train.py --save-checkpoint first.')
    weights = torch.load(args.transport_checkpoint, map_location='cpu', weights_only=True)
    size = int(weights['size'])
    if args.demo:
        mask = synthetic_masks(1, size, 2026)[0]
        source = 'synthetic phase map'
    elif args.mask is not None:
        mask = read_mask(args.mask, size)
        source = str(args.mask)
    else:
        mask = infer_segmentation(args.image, args.sem_checkpoint, size)
        source = str(args.image)
    report = run(mask, args.transport_checkpoint, args.k)
    report['input_type'] = 'demo' if args.demo else ('NASA mask' if args.mask else 'SEM image / trained U-Net')
    report['input_path'] = source
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
