# SEM segmentation and physics-informed conduction: methods and findings

## Research question

Does a finite-volume conservation loss improve a convolutional surrogate for heterogeneous 2-D conduction, and does additional supervised flux regularization improve its modeled effective-conductivity proxy?

## Source constraints

The NASA EBC annotations use background=0, oxide=1, crack=2. The linked U-Net has held-out foreground IoU 0.439 and crack IoU 0.126, but the trained weight file is not present. The proposed physical values for the three semantic classes are not experimentally calibrated. The y direction is a provisional proxy for cross-sectional through-thickness conduction, not a verified image orientation.

## Numerical formulation

For zero-source steady-state conduction, solve div(k grad T)=0 using harmonic-mean conductance at cell interfaces, imposed temperatures 1 and 0 at opposing edges, insulated top/bottom edges, and sparse linear algebra. CNN boundaries are embedded, and models are trained with a numerical-temperature MSE, an optional node flux-balance penalty, and optionally the squared relative error of numerical boundary flux. The last component uses supervised numerical targets and must not be confused with independently validated physics.

## Controlled experiment

Synthetic 24x24 three-class maps: 48 training, 16 validation, 24 test. Oxide k is sampled uniformly 0.15–0.75, crack 0.015–0.12, background k=1; all are hypothetical relative conductivities. Both image-flow orientations are represented by rotation. Three model initialization seeds (5,17,29) are measured on the same fixed held-out synthetic geometries. Comparison metrics: temperature MAE, discrete residual, modeled boundary-conductivity proxy error, and CNN-versus-FVM inference time (without training).

Unit tests cover homogeneous solutions in both directions, layer parallel-versus-through transport, conservation, and original-mask resizing loss. NASA EBC1–3 real held-out *annotation* masks can be downloaded separately for coarsening checks, sensitivity to conductivity scenarios and out-of-domain synthetic-CNN comparison. Those masks do not provide measured heat flux or experimental k, and the trained SEM segmentation model is not invoked without its weights.

## Interpretation and necessary next evidence

Only a synthetic numerical surrogate is verified. Adding a PDE residual alone may decrease node conservation error while leaving effective-conductivity proxy error high; adding supervised boundary flux can improve the latter. The finite-volume solver produces both target and training penalty, so this is not independent physics verification. Reported batch speedup applies only to small CPU masks, not full-resolution SEM images.

Physical validation requires the original checkpoint and matched SEM images, correct sample orientation and pixel scale, reliable phase/material identification, native-resolution crack validation, measured phase and interface properties, and comparison against independent experimental heat-flux data or higher-fidelity simulations. A 2-D image cannot establish 3-D connectivity or service life.

References: https://github.com/nasa/pretrained-microscopy-models ; https://github.com/nasa/AQUAMI-TGO ; https://doi.org/10.1016/j.icheatmasstransfer.2026.111898

## Verified NASA annotation transfer (three held-out masks)

The GitHub scientific-validation workflow completed the three-model synthetic benchmark and then downloaded three original 1024×1024 NASA test annotations. The transport CNN, trained exclusively on synthetic 24×24 masks, was compared with a finite-volume solve on the **same coarsened mask**. Effective-conductivity proxy relative errors were **50.2% (EBC1), 29.8% (EBC2), and 18.9% (EBC3)**. EBC2 lost all annotated crack pixels when downsampled to 24×24; the other two masks also showed substantial crack-fraction distortion.

Consequently, the present pretrained surrogate **fails the real-geometry transfer check** and should not be used to infer actual EBC thermal performance. The recommended numerical research path is annotation-based finite-volume analysis with a recorded resolution and crack-loss audit; the existing 24px CNN remains a synthetic benchmark only. Improving generalization would require training on original-resolution or tiled real geometry using NASA training/validation partitions, re-checking crack preservation, and then independently evaluating on held-out cases. The current NASA test masks must not be reused for model tuning.

These outcomes are negative but useful results. They locate the main shortcomings in geometric fidelity and domain transfer, rather than suggesting that higher synthetic test scores alone establish practical predictive power.

[Full NASA annotation results](results/real_annotations/nasa_ebc_cases.md) | [Synthetic comparison](results/v2/benchmark.md)
