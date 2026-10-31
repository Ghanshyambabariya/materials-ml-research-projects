"""Reproducible synthetic-only benchmark: CNN vs CNN with PDE residual."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from time import perf_counter

import numpy as np
import torch
from torch import nn

from model import TransportCNN, physics_residual
from physics import conductivity, effective_conductivity, solve_temperature, synthetic_masks

ROOT = Path(__file__).resolve().parent


def prepare(count, size, seed, conductivities):
    masks = synthetic_masks(count, size, seed)
    maps = np.stack([conductivity(mask, conductivities) for mask in masks])
    temperatures = np.stack([solve_temperature(k) for k in maps])
    return (torch.tensor(masks, dtype=torch.long),
            torch.tensor(maps, dtype=torch.float32),
            torch.tensor(temperatures, dtype=torch.float32))


def metrics(model, data):
    labels, k, target = data
    model.eval()
    with torch.no_grad():
        pred = model(labels, k)
        mae = float((pred - target).abs().mean())
        pde = float(physics_residual(pred, k).square().mean().sqrt())
        bound_violation = float(((pred < -1e-6) | (pred > 1 + 1e-6)).float().mean())
        flux_errors = []
        for i in range(len(labels)):
            actual_k = k[i].numpy()
            ref = effective_conductivity(actual_k, target[i].numpy())
            est = effective_conductivity(actual_k, pred[i].numpy())
            flux_errors.append(abs(est-ref) / abs(ref))
    return {
        "temperature_mae": round(mae, 6),
        "pde_residual_rmse": round(pde, 6),
        "mean_relative_effective_conductivity_error": round(float(np.mean(flux_errors)), 6),
        "temperature_bounds_violation_rate": round(bound_violation, 6),
    }


def fit(train, val, physics_weight, epochs, width, seed):
    torch.manual_seed(seed)
    net = TransportCNN(width=width)
    optimizer = torch.optim.Adam(net.parameters(), lr=0.002)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=epochs)
    x, k, t = train
    xv, kv, tv = val
    best = float('inf')
    best_state = None
    history = []
    start = perf_counter()
    for epoch in range(epochs):
        net.train()
        order = torch.randperm(len(x))
        for batch_ids in order.split(16):
            predicted = net(x[batch_ids], k[batch_ids])
            mse = (predicted-t[batch_ids]).square().mean()
            residual = physics_residual(predicted, k[batch_ids]).square().mean()
            bounds = ((-predicted).relu().square() + (predicted - 1).relu().square()).mean()
            loss = mse + physics_weight*residual + 0.5*bounds
            optimizer.zero_grad()
            loss.backward()
            nn.utils.clip_grad_norm_(net.parameters(), 2.0)
            optimizer.step()
        scheduler.step()
        net.eval()
        with torch.no_grad():
            prediction = net(xv, kv)
            val_mse = float((prediction-tv).square().mean())
        if val_mse < best:
            best = val_mse
            best_state = {name: value.detach().clone() for name, value in net.state_dict().items()}
        if epoch in {0, epochs//4-1, epochs//2-1, epochs-1}:
            history.append({"epoch": epoch+1, "validation_mse": round(val_mse, 7)})
    net.load_state_dict(best_state)
    return net, round(perf_counter()-start, 3), history


def experiment(epochs=80, train_count=64, size=24, width=24, seed=17, conductivities=(1.0,0.4,0.05), save_checkpoint=False):
    torch.set_num_threads(min(torch.get_num_threads(), 2))
    training = prepare(train_count, size, seed, conductivities)
    validation = prepare(16, size, seed+1, conductivities)
    test = prepare(20, size, seed+2, conductivities)
    baseline = torch.linspace(1, 0, size).view(1,1,size).expand(len(test[0]),size,size)
    linear_model = {
        "temperature_mae": round(float((baseline-test[2]).abs().mean()), 6),
        "pde_residual_rmse": round(float(physics_residual(baseline, test[1]).square().mean().sqrt()), 6),
    }
    results = {}
    best_model = None
    for name, alpha in [("cnn_data_only", 0.0), ("physics_informed_cnn", 0.5)]:
        net, seconds, history = fit(training, validation, alpha, epochs, width, seed)
        results[name] = {"physics_residual_weight": alpha, "train_seconds": seconds,
                         "test": metrics(net, test), "history": history}
        if name == "physics_informed_cnn":
            best_model = net
    outcome = {
        "dataset_type": "synthetic 3-class masks; not measured SEM images",
        "n_train": train_count, "n_val": 16, "n_test": 20,
        "mask_shape": [size,size], "seed": seed, "epochs": epochs, "network_width": width,
        "phase_labels": {"0":"background", "1":"oxide", "2":"crack"},
        "assumed_relative_conductivities": list(conductivities),
        "equation": "div(k grad T)=0",
        "boundary_conditions": "left=1, right=0, top/bottom insulated",
        "linear_profile_baseline": linear_model,
        "models": results,
        "checkpoint_note": "Transport CNN trained on synthetic maps; separate from pretrained SEM U-Net weights",
        "interpretation": "Numerical surrogate benchmark only; no measured thermal conductivity, lifetime, or material-property prediction.",
    }
    if save_checkpoint:
        ROOT.joinpath('results').mkdir(exist_ok=True)
        torch.save({"model_state":best_model.state_dict(), "width":width, "size":size,
                    "relative_conductivities":conductivities, "training_type":"synthetic"},
                   ROOT/'results'/'transport_cnn_synthetic.pt')
    return outcome


def save(outcome, folder):
    folder.mkdir(parents=True, exist_ok=True)
    (folder/'benchmark.json').write_text(json.dumps(outcome, indent=2)+'\n', encoding='utf-8')
    a = outcome['models']['cnn_data_only']['test']
    b = outcome['models']['physics_informed_cnn']['test']
    lines = ["# Physics-informed SEM transport: synthetic benchmark", "",
        "The mask generator is synthetic; no pretrained SEM checkpoint was used in this benchmark.",
        "NASA EBC phase names are background, oxide, crack. Conductivities are illustrative ratios (1.0, 0.4, 0.05).",
        "", "Steady-state equation: ∇·(k∇T) = 0. Left/right temperature fixed; upper/lower edges insulated.", "",
        "| Test metric | CNN (data only) | CNN + finite-volume physics loss |", "|---|---:|---:|",
        f"| Mean absolute temperature error | {a['temperature_mae']:.6f} | {b['temperature_mae']:.6f} |",
        f"| PDE residual RMSE | {a['pde_residual_rmse']:.6f} | {b['pde_residual_rmse']:.6f} |",
        f"| Relative effective-conductivity error | {a['mean_relative_effective_conductivity_error']:.3%} | {b['mean_relative_effective_conductivity_error']:.3%} |",
        f"| Unphysical temperature fraction | {a['temperature_bounds_violation_rate']:.3%} | {b['temperature_bounds_violation_rate']:.3%} |",
        "", f"Uniform-temperature-profile baseline MAE: {outcome['linear_profile_baseline']['temperature_mae']:.6f}.",
        "", "Data uses a numerical finite-volume solver for labels, and its residual also provides physics guidance.",
        "**Important:** These are modeled, dimensionless transport results. They do not establish experimental thermal conductivity, oxidation lifetime or actual SEM performance.", ""]
    (folder/'benchmark.md').write_text('\n'.join(lines), encoding='utf-8')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Compare data-only CNN and physics-informed CNN on synthetic microstructures.')
    parser.add_argument('--epochs', type=int, default=80)
    parser.add_argument('--size', type=int, default=24)
    parser.add_argument('--train-count', type=int, default=64)
    parser.add_argument('--save-checkpoint', action='store_true')
    args = parser.parse_args()
    if args.epochs < 1 or args.size < 8 or args.train_count < 4:
        parser.error('epochs>=1, size>=8 and train-count>=4 are required')
    result = experiment(epochs=args.epochs, size=args.size, train_count=args.train_count, save_checkpoint=args.save_checkpoint)
    save(result, ROOT/'results')
    print(json.dumps({"data_only":result['models']['cnn_data_only']['test'],
                      "physics_informed":result['models']['physics_informed_cnn']['test']}, indent=2))
