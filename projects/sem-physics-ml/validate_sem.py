"""Evaluate 0/1/2 NASA EBC annotations and optional trained U-Net predictions."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import numpy as np
from PIL import Image
import matplotlib.pyplot as plt
from physics import conductivity
from methods import audit_resizing, directional_solution, per_class_iou, phase_descriptors

SCENARIOS = {"low_contrast": (1., .75, .12),
             "medium_contrast": (1., .4, .05),
             "high_contrast": (1., .15, .015)}


def read_native_mask(path):
    with Image.open(path) as f:
        mask = np.array(f)
    conductivity(mask)
    return mask.astype(np.uint8)


def analyze_mask(mask, size=72, direction="y", scenarios=None):
    audit = audit_resizing(mask, size)
    small = audit.pop("coarse_mask")
    result = {"source_size": list(mask.shape), "geometry_original": phase_descriptors(mask),
              "coarsening": audit, "geometry_coarse": phase_descriptors(small),
              "direction": direction, "scenarios": {},
              "calibration_status": "Uncalibrated material parameters; numerical illustration only."}
    for name, values in (scenarios or SCENARIOS).items():
        s = directional_solution(small, values=values, direction=direction)
        result["scenarios"][name] = {"relative_k": list(values),
           "modeled_conductivity_proxy": s["conductivity_proxy"], "conservation": s["conservation"]}
    result["_mask_for_plot"] = small
    return result


def compare_masks(truth_mask, prediction_mask, size=72, direction="y"):
    if truth_mask.shape != prediction_mask.shape:
        raise ValueError("Masks must be registered to the same pixel grid")
    a = analyze_mask(truth_mask, size, direction)
    b = analyze_mask(prediction_mask, size, direction)
    changes = {}
    for name in a["scenarios"]:
        reference = a["scenarios"][name]["modeled_conductivity_proxy"]
        predicted = b["scenarios"][name]["modeled_conductivity_proxy"]
        changes[name] = {"ground_truth_proxy": reference, "prediction_proxy": predicted,
                         "absolute_relative_change": abs(predicted-reference)/max(abs(reference),1e-12)}
    a.pop("_mask_for_plot")
    b.pop("_mask_for_plot")
    return {"class_iou": per_class_iou(truth_mask, prediction_mask),
            "truth": a, "prediction": b, "scenario_change": changes,
            "note": "Changes follow from input masks and assumed coefficients, not measured thermal conductivity."}


def save_figure(mask, path, direction="y"):
    field = directional_solution(mask, direction=direction)["temperature"]
    fig, axes = plt.subplots(1, 2, figsize=(8, 4), layout="constrained")
    axes[0].imshow(mask, cmap="viridis", vmin=0, vmax=2, interpolation="nearest")
    axes[0].set_title("EBC phase annotation")
    axes[1].imshow(field, cmap="inferno", vmin=0, vmax=1)
    axes[1].set_title("Modeled temperature ("+direction+")")
    for ax in axes:
        ax.set_xticks([])
        ax.set_yticks([])
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=150)
    plt.close(fig)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--mask", type=Path, required=True)
    p.add_argument("--predicted-mask", type=Path)
    p.add_argument("--image", type=Path)
    p.add_argument("--sem-checkpoint", type=Path)
    p.add_argument("--direction", choices=["x","y"], default="y")
    p.add_argument("--size", type=int, default=72)
    p.add_argument("--out", type=Path, default=Path(__file__).resolve().parent/"results/sem_case")
    args = p.parse_args()
    if args.size < 8:
        p.error("size must be >=8")
    if (args.image is None) != (args.sem_checkpoint is None):
        p.error("--image and --sem-checkpoint must be supplied together")
    if args.predicted_mask and args.image:
        p.error("Choose predicted mask or image/checkpoint")
    ground_truth = read_native_mask(args.mask)
    args.out.mkdir(parents=True, exist_ok=True)
    if args.predicted_mask:
        result = compare_masks(ground_truth, read_native_mask(args.predicted_mask), args.size, args.direction)
    elif args.image:
        from predict import infer_segmentation
        predicted = infer_segmentation(args.image, args.sem_checkpoint, 256)
        ground_truth_256 = np.asarray(Image.fromarray(ground_truth).resize(
            (256,256), Image.Resampling.NEAREST))
        result = compare_masks(ground_truth_256, predicted, args.size, args.direction)
        result["original_mask_resolution"] = list(ground_truth.shape)
        result["segmentation_checkpoint"] = str(args.sem_checkpoint)
    else:
        result = analyze_mask(ground_truth, args.size, args.direction)
        save_figure(result.pop("_mask_for_plot"), args.out/"case.png", args.direction)
    result["input_annotation"] = args.mask.name
    (args.out/"case.json").write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"annotation":args.mask.name,"out":str(args.out/"case.json")},indent=2))


if __name__ == "__main__":
    main()
