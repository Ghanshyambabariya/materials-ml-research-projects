# SEM Physics-Informed ML

This is a separate project that builds on the existing NASA EBC segmentation model. It combines an image segmentation mask with a physics-informed convolutional neural network to predict a **dimensionless two-dimensional heat-transport field**.

## How it connects to the trained SEM model

1. Existing UNetSmall predicts a three-class segmentation from an SEM image: background (0), oxide (1), crack (2).
2. The mask is converted to an assumed phase-conductivity map.
3. A finite-volume solver supplies reference temperature fields.
4. An ANN/CNN learns temperature fields, with a heat-equation residual added to its training loss.
5. The output reports a temperature field, model error and a modeled effective-conductivity proxy.

The SEM U-Net's results are already in the [segmentation project](../sem-segmentation). **Its trained checkpoint is not committed to GitHub**, so inference on actual SEM images requires your locally saved sem_ebc_unet.pt. The pipeline never substitutes random U-Net weights.

## Physics

Solve ∇·(k∇T) = 0 with left T=1, right T=0, and insulating top/bottom. The reference is a five-point finite-volume solve with harmonic conductivity at phase boundaries. The ANN has the two Dirichlet boundaries enforced by its architecture; the training loss includes both data error and the finite-volume residual.

The assumed normalized phase conductivities are 1.0, 0.4 and 0.05 (background, oxide, crack). **These are illustrative choices, not measured thermal properties.** A 2-D cross-section does not establish true 3-D thermal conductivity or service life.

## Reproduce

From the repository root:

```bash
python -m pip install torch numpy scipy pillow torchvision pytest
python -m pytest -q tests/test_sem_physics_ml.py
python projects/sem-physics-ml/train.py --epochs 160 --save-checkpoint
python projects/sem-physics-ml/predict.py --demo
```

The benchmark trains on 64 artificially generated phase masks, validates on 16 different masks, and tests on 20 additional masks. Masks are 24×24 pixels. Both the CNN without physics loss and the CNN with physics loss use the same architecture and independent numerical temperature references. The results are **synthetic numerical experiments, not measured SEM results**.

Run on your own NASA EBC image and trained U-Net checkpoint:

```bash
python projects/sem-physics-ml/predict.py --image /path/to/sem_image.tif --sem-checkpoint /path/to/sem_ebc_unet.pt
```

Or bypass the U-Net using a NASA EBC annotation:

```bash
python projects/sem-physics-ml/predict.py --mask /path/to/ebc_label_mask.tif
```

The script requires the trained transport-model checkpoint at results/transport_cnn_synthetic.pt. If unavailable, run train.py with --save-checkpoint first. It resizes phase masks to 24×24 with nearest-neighbor sampling. **Small cracks may disappear**, so the current model is a demonstration and cannot yet quantify real coating behavior.

## Goals and evidence

- Goal 1: improve the synthetic test temperature error and PDE residual versus an ordinary data-only CNN. The 160-epoch experiment meets both checks.
- Goal 2: measure how the real trained SEM segmentation affects a heat-transport proxy versus the annotated mask. The adapter is implemented, but cannot be validated until the actual segmentation weights and image/mask data are supplied.

[Experiment notes](research_report.md) | [Synthetic benchmark](results/benchmark.md)

Sources: [NASA EBC labels](https://github.com/nasa/pretrained-microscopy-models), [Stuckner et al., 2022](https://doi.org/10.1038/s41524-022-00878-5), [2-D versus 3-D microstructure limitation](https://pmc.ncbi.nlm.nih.gov/articles/PMC11620251/).
